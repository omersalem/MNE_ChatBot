import json
import logging
import re
import time
from flask import Blueprint, request, Response, jsonify, stream_with_context
from config import Config
from providers.provider_manager import ProviderManager
from rag.retrieval import RetrievalEngine
from utils.group_manager import GroupManager
from sync.processor import DocumentProcessor

logger = logging.getLogger(__name__)

chat_bp = Blueprint('chat', __name__)
retrieval = RetrievalEngine()
manager = ProviderManager()
group_manager = GroupManager()
processor = DocumentProcessor()

FALLBACK_ANSWER_EN = "We do not currently have enough verified information to answer that question."
FALLBACK_ANSWER_AR = "\u0644\u0627 \u062a\u062a\u0648\u0641\u0631 \u0644\u062f\u064a\u0646\u0627 \u062d\u0627\u0644\u064a\u0627\u064b \u0645\u0639\u0644\u0648\u0645\u0627\u062a \u0645\u0648\u062b\u0648\u0642\u0629 \u0643\u0627\u0641\u064a\u0629 \u0644\u0644\u0625\u062c\u0627\u0628\u0629 \u0639\u0644\u0649 \u0647\u0630\u0627 \u0627\u0644\u0633\u0624\u0627\u0644."
ARABIC_CHAR_PATTERN = re.compile(r'[\u0600-\u06FF]')
LATIN_CHAR_PATTERN = re.compile(r'[A-Za-z]')

SYSTEM_PROMPT = """You are a professional enterprise assistant.

Answer ONLY from the reference material provided below.

Rules:
- Do not mention documents, uploads, files, sources, or the knowledge base.
- Do not say that the answer was or was not found in a document.
- Language rule: {language_instruction}
- Treat indirect, paraphrased, synonym-based, and category-style questions as valid when the reference material contains equivalent concepts, legal forms, steps, requirements, benefits, goals, or obligations.
- Connect related excerpts when the answer spans more than one reference excerpt, and present the combined result as one coherent answer.
- If the user asks indirectly about goals, benefits, starting, creating, registering, requirements, types, or procedures, answer with the closest supported information from the reference material instead of refusing.
- Prefer the most specific supported section title or clause when it clearly matches the user's intent, even if the wording is not identical.
- If reference excerpts are provided, you MUST answer from them and MUST NOT use the fallback sentence.
- If the reference material is insufficient, respond with this exact sentence and nothing else:
  {fallback_sentence}
- Keep the answer professional, clear, and sufficiently complete.
- Start with a direct answer.
- Use short bullet points or numbering when they improve clarity.
- Include exact names, versions, numbers, and steps only when they are supported by the reference material.
- When the reference material lists goals, benefits, requirements, or steps, include the full supported list instead of a partial answer.

Reference material:
{context}"""

RESCUE_PROMPT_TEMPLATE = """You are a professional enterprise assistant.

Answer ONLY from the reference material below.

Rules:
- Answer in {language_name} only.
- Relevant reference excerpts are already available, so DO NOT return the fallback sentence.
- Give the closest supported answer even if the user's wording is indirect, shorter, broader, or phrased differently.
- For steps, requirements, conditions, obligations, goals, or definitions, summarize the supported points clearly and directly.
- If the material supports only part of the request, answer with that supported part without refusing.
- Do not mention documents, files, sources, or the knowledge base.
- Start with a direct answer.

Reference material:
{context}"""


def detect_response_language(message):
    arabic_count = len(ARABIC_CHAR_PATTERN.findall(message))
    latin_count = len(LATIN_CHAR_PATTERN.findall(message))
    if arabic_count > latin_count:
        return 'ar'
    return 'en'


def language_instruction_for(lang):
    if lang == 'ar':
        return "If the user's question is in Arabic, answer in Arabic only."
    return "If the user's question is in English, answer in English only."


def fallback_for(lang):
    return FALLBACK_ANSWER_AR if lang == 'ar' else FALLBACK_ANSWER_EN


def language_name_for(lang):
    return 'Arabic' if lang == 'ar' else 'English'


def normalize_answer_text(text):
    return re.sub(r'\s+', ' ', (text or '')).strip()


def strip_fallback_from_answer(answer, fallback_sentence):
    answer = (answer or '').strip()
    fallback_sentence = (fallback_sentence or '').strip()
    if not answer or not fallback_sentence:
        return answer

    cleaned = answer.replace(fallback_sentence, '').strip()
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned).strip()
    return cleaned


def answer_uses_fallback(answer, fallback_sentence):
    normalized_answer = normalize_answer_text(answer)
    normalized_fallback = normalize_answer_text(fallback_sentence)
    if not normalized_answer or not normalized_fallback:
        return False
    return normalized_fallback in normalized_answer


def should_retry_with_rescue(answer, fallback_sentence, sources):
    if not sources:
        return False
    return answer_uses_fallback(answer, fallback_sentence)


def finalize_answer(answer, fallback_sentence, sources):
    answer = (answer or '').strip()
    if not sources:
        return answer or fallback_sentence

    cleaned = strip_fallback_from_answer(answer, fallback_sentence)
    return cleaned or answer or fallback_sentence


def ensure_sources_indexed(source_files):
    if not source_files:
        return

    indexed_sources = retrieval.vector_store.get_indexed_sources()
    for source_file in source_files:
        if source_file in indexed_sources:
            continue

        file_path = Config.COMPANY_DOCS_DIR / source_file
        if not file_path.exists() or not file_path.is_file():
            continue

        logger.info("Auto-indexing missing source before chat: %s", source_file)
        processor.process_file(file_path)
        indexed_sources.add(source_file)


def ensure_index_ready(source_files=None):
    source_files = source_files or []

    if retrieval.vector_store.requires_reindex or retrieval.vector_store.is_empty():
        logger.info("Vector store is empty or requires reindex; indexing available documents")
        if source_files:
            ensure_sources_indexed(source_files)
        else:
            processor.process_all()
        retrieval.vector_store.requires_reindex = False
        return

    if source_files:
        ensure_sources_indexed(source_files)


@chat_bp.route('/api/chat', methods=['POST'])
def chat():
    data = request.get_json() or {}
    message = (data.get('message') or '').strip()
    provider_name = data.get('provider', manager.get_active_name())
    group_id = (data.get('group_id') or '').strip()

    if not message:
        return jsonify({'error': 'Message is required'}), 400

    try:
        response_lang = detect_response_language(message)
        fallback_sentence = fallback_for(response_lang)

        allowed_sources = None
        if group_id:
            selected_group = group_manager.get_group(group_id)
            if selected_group:
                allowed_sources = selected_group.get('documents', [])
        ensure_index_ready(allowed_sources)

        context, sources = retrieval.retrieve(message, allowed_sources=allowed_sources)
        if not context:
            def generate_fallback():
                yield f"data: {json.dumps({'content': fallback_sentence})}\n\n"
                yield f"data: {json.dumps({'sources': []})}\n\n"
                yield "data: [DONE]\n\n"

            return Response(
                stream_with_context(generate_fallback()),
                mimetype='text/event-stream',
                headers={
                    'Cache-Control': 'no-cache',
                    'X-Accel-Buffering': 'no',
                    'Connection': 'keep-alive',
                }
            )

        system_prompt = SYSTEM_PROMPT.format(
            context=context,
            language_instruction=language_instruction_for(response_lang),
            fallback_sentence=fallback_sentence,
        )

        messages = [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': message},
        ]

        provider = manager.get_provider(provider_name)

        def generate():
            start_time = time.time()
            try:
                chunks = []
                for chunk in provider.stream_response(
                    messages,
                    temperature=Config.ANSWER_TEMPERATURE,
                    max_tokens=Config.ANSWER_MAX_TOKENS,
                ):
                    chunks.append(chunk)

                answer_text = ''.join(chunks).strip()
                answer_text = finalize_answer(answer_text, fallback_sentence, sources)

                if should_retry_with_rescue(answer_text, fallback_sentence, sources):
                    rescue_prompt = RESCUE_PROMPT_TEMPLATE.format(
                        context=context,
                        language_name=language_name_for(response_lang),
                    )
                    rescue_messages = [
                        {'role': 'system', 'content': rescue_prompt},
                        {'role': 'user', 'content': message},
                    ]
                    rescue_answer = provider.generate_response(
                        rescue_messages,
                        temperature=0,
                        max_tokens=Config.ANSWER_MAX_TOKENS,
                    )
                    answer_text = finalize_answer(rescue_answer, fallback_sentence, sources)

                data_line = json.dumps({'content': answer_text})
                yield f"data: {data_line}\n\n"

                sources_line = json.dumps({'sources': sources})
                yield f"data: {sources_line}\n\n"
                yield "data: [DONE]\n\n"
                logger.info("Chat completed in %.2fs using provider=%s group=%s", time.time() - start_time, provider_name, group_id or 'none')
            except TimeoutError as e:
                logger.error(f"Stream timeout: {e}")
                error_line = json.dumps({'error': 'Request timed out. Check your API key and try again.'})
                yield f"data: {error_line}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as e:
                logger.error(f"Stream error: {e}")
                error_line = json.dumps({'error': str(e)})
                yield f"data: {error_line}\n\n"
                yield "data: [DONE]\n\n"

        return Response(
            stream_with_context(generate()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no',
                'Connection': 'keep-alive',
            }
        )

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return jsonify({'error': str(e)}), 500


@chat_bp.route('/api/suggested-questions', methods=['GET'])
def suggested_questions():
    from sync.suggested_questions import SuggestedQuestions
    sq = SuggestedQuestions()
    questions = sq.get_questions()
    return jsonify({'questions': questions})


@chat_bp.route('/api/suggested-questions/refresh', methods=['POST'])
def refresh_questions():
    from sync.suggested_questions import SuggestedQuestions
    sq = SuggestedQuestions()
    questions = sq.refresh()
    return jsonify({'questions': questions})


@chat_bp.route('/api/groups', methods=['GET'])
def groups():
    docs = []
    for ext in Config.ALLOWED_EXTENSIONS:
        for file_path in Config.COMPANY_DOCS_DIR.glob(f'*.{ext}'):
            docs.append(file_path.name)
    group_manager.prune_missing_documents(docs)
    return jsonify({'groups': group_manager.list_groups()})
