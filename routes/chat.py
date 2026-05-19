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
- Treat indirect, paraphrased, and category-style questions as valid when the reference material contains equivalent concepts, legal forms, steps, or requirements.
- If the user asks about types, categories, requirements, or procedures indirectly, answer with the closest supported information from the reference material instead of refusing.
- If the reference material is insufficient, respond with this exact sentence and nothing else:
  {fallback_sentence}
- Keep the answer concise, professional, and well organized.
- Start with a direct answer.
- Use short bullet points only when they improve clarity.
- Include exact names, versions, numbers, and steps only when they are supported by the reference material.

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
                ensure_sources_indexed(allowed_sources)

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
                for chunk in provider.stream_response(
                    messages,
                    temperature=Config.ANSWER_TEMPERATURE,
                    max_tokens=Config.ANSWER_MAX_TOKENS,
                ):
                    data_line = json.dumps({'content': chunk})
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
