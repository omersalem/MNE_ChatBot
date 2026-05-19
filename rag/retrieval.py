import logging
import re

from config import Config
from rag.vector_store import VectorStore

logger = logging.getLogger(__name__)


class RetrievalEngine:
    STOPWORDS = {
        'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from', 'how',
        'in', 'is', 'it', 'of', 'on', 'or', 'that', 'the', 'this', 'to', 'was',
        'what', 'when', 'where', 'which', 'who', 'why', 'with', 'your',
    }
    ARABIC_STOPWORDS = {
        'الى', 'إلى', 'في', 'من', 'على', 'عن', 'ما', 'ماذا', 'كيف', 'هل',
        'هذا', 'هذه', 'ذلك', 'تلك', 'هناك', 'هنا', 'ثم', 'او', 'أو', 'و',
        'يا', 'تم', 'يتم', 'هي', 'هو', 'هم', 'هن', 'كما', 'كل', 'أي', 'اي',
        'لم', 'لن', 'قد', 'لقد', 'إن', 'ان', 'اذا', 'إذا', 'بعد', 'قبل',
        'مع', 'ضمن', 'حول', 'عند', 'لدى', 'بين', 'حتى',
    }
    ARABIC_CHAR_PATTERN = re.compile(r'[\u0600-\u06FF]')

    def __init__(self):
        self.vector_store = VectorStore()

    def retrieve(self, query, top_k=None, allowed_sources=None):
        top_k = top_k or Config.TOP_K
        logger.info("Retrieving top-%s chunks for query", top_k)

        profile = self._build_query_profile(query)
        candidate_count = max(top_k, getattr(Config, 'SEARCH_CANDIDATES', top_k))

        vector_results = self._vector_search(profile, candidate_count, allowed_sources)
        keyword_results = self._keyword_search(profile, allowed_sources=allowed_sources, top_k=candidate_count)
        results = self._merge_candidate_results(vector_results, keyword_results, top_k=candidate_count)
        results = self._rerank_results(profile, results, top_k)

        if not results:
            logger.info("No relevant chunks found")
            return '', []

        context = self._build_context(results)
        sources = self._build_sources(results)
        return context, sources

    def _build_context(self, results):
        seen_chunks = set()
        context_parts = []
        total_length = 0

        for i, result in enumerate(results, start=1):
            if result['chunk_id'] in seen_chunks:
                continue
            seen_chunks.add(result['chunk_id'])

            chunk_text = f"Reference excerpt {i}:\n{result['text']}"
            if total_length + len(chunk_text) > Config.MAX_CONTEXT_TOKENS * 4:
                break

            context_parts.append(chunk_text)
            total_length += len(chunk_text)

        return '\n\n---\n\n'.join(context_parts)

    def _build_sources(self, results):
        seen = set()
        sources = []
        for result in results:
            key = (result['source_file'], result['chunk_id'])
            if key in seen:
                continue
            seen.add(key)
            sources.append({
                'filename': result['source_file'],
                'chunk_id': result['chunk_id'],
                'score': result['score'],
            })
        return sources

    def _build_query_profile(self, query):
        normalized_query = self._normalize_text(query)
        query_terms = self._tokenize(query)
        is_arabic_query = bool(self.ARABIC_CHAR_PATTERN.search(query))

        asks_for_steps = any(term in normalized_query for term in ('كيف', 'اجراء', 'خطوات', 'طريقه', 'طريقة'))
        asks_about_registration = 'تسجيل' in normalized_query and any(
            token in normalized_query for token in ('شرك', 'تاجر', 'مؤسسه', 'مؤسسة')
        )
        asks_about_requirements = any(term in normalized_query for term in ('وثائق', 'مستندات', 'اوراق', 'أوراق', 'شروط'))
        asks_about_types = (
            any(term in normalized_query for term in ('انواع', 'أنواع', 'نوع', 'اشكال', 'أشكال', 'شكل قانوني', 'الشكل القانوني'))
            and any(token in normalized_query for token in ('شرك', 'مشروع', 'تاجر'))
        )

        boost_phrases = []
        if asks_for_steps:
            boost_phrases.extend([
                'خطوات التسجيل',
                'اجراءات التسجيل',
                'طريقة التسجيل',
            ])
        if asks_about_registration:
            boost_phrases.extend([
                'تسجيل الشركة',
                'تسجيل شركة',
                'وزارة الاقتصاد الوطني',
                'مركز خدمات الجمهور',
            ])
        if asks_about_requirements:
            boost_phrases.extend([
                'الوثائق التالية',
                'الاوراق المطلوبة',
                'المستندات المطلوبة',
                'نسخ من',
            ])
        if asks_about_types:
            boost_phrases.extend([
                'الشكل القانوني',
                'الاشكال القانونية',
                'الأشكال القانونية',
                'ما هو الشكل القانوني المناسب لعملك',
                'شهادة تسجيل التاجر',
                'شركة عادية عامة',
                'شركة عادية محدودة',
                'شركة مساهمة خصوصية',
                'شركة مدنية',
            ])

        semantic_terms = set(query_terms)
        for phrase in boost_phrases:
            semantic_terms.update(self._tokenize(phrase))

        vector_queries = [query]
        compact_terms = sorted(semantic_terms, key=len, reverse=True)
        if compact_terms:
            vector_queries.append(' '.join(compact_terms[:12]))
        if boost_phrases:
            vector_queries.append(' '.join(boost_phrases[:8]))
        if asks_about_types:
            vector_queries.append('انواع الشركات الاشكال القانونية الشكل القانوني شركة عادية عامة شركة عادية محدودة شركة مساهمة خصوصية شركة مدنية')

        deduped_vector_queries = []
        seen_queries = set()
        for item in vector_queries:
            cleaned = item.strip()
            if not cleaned:
                continue
            normalized_item = self._normalize_text(cleaned)
            if normalized_item in seen_queries:
                continue
            seen_queries.add(normalized_item)
            deduped_vector_queries.append(cleaned)

        return {
            'query': query,
            'normalized_query': normalized_query,
            'query_terms': query_terms,
            'semantic_terms': semantic_terms,
            'boost_phrases': boost_phrases,
            'vector_queries': deduped_vector_queries,
            'is_arabic_query': is_arabic_query,
            'asks_for_steps': asks_for_steps,
            'asks_about_registration': asks_about_registration,
            'asks_about_requirements': asks_about_requirements,
            'asks_about_types': asks_about_types,
        }

    def _vector_search(self, profile, candidate_count, allowed_sources=None):
        merged = {}

        for idx, vector_query in enumerate(profile['vector_queries']):
            weight = 1.0 if idx == 0 else 0.96
            results = self.vector_store.search(
                vector_query,
                top_k=candidate_count,
                allowed_sources=allowed_sources,
            )
            for result in results:
                chunk_id = result['chunk_id']
                adjusted_score = result['score'] * weight
                existing = merged.get(chunk_id)
                if not existing or adjusted_score > existing['score']:
                    merged[chunk_id] = {
                        **result,
                        'score': adjusted_score,
                    }

        ranked = list(merged.values())
        ranked.sort(key=lambda item: item.get('score', 0), reverse=True)
        return ranked[:candidate_count]

    def _rerank_results(self, profile, results, top_k):
        if not results:
            return []

        query_terms = profile['query_terms']
        semantic_terms = profile['semantic_terms']
        boost_phrases = profile['boost_phrases']
        normalized_query = profile['normalized_query']
        is_arabic_query = profile['is_arabic_query']
        reranked = []

        for result in results:
            normalized_text = self._normalize_text(result['text'])
            text_terms = self._tokenize(result['text'])

            direct_overlap = len(query_terms & text_terms)
            semantic_overlap = len(semantic_terms & text_terms)
            overlap_denominator = max(len(query_terms), len(semantic_terms), 1)
            overlap_ratio = semantic_overlap / overlap_denominator

            phrase_matches = sum(1 for phrase in boost_phrases if self._normalize_text(phrase) in normalized_text)
            phrase_boost = min(phrase_matches * 0.07, 0.28)
            exact_phrase_boost = 0.08 if normalized_query and normalized_query in normalized_text else 0.0
            filename_boost = 0.04 if any(term in self._normalize_text(result['source_file']) for term in query_terms) else 0.0
            intent_boost = self._intent_boost(profile, normalized_text)

            hybrid_score = (
                (result['score'] * 0.56)
                + (overlap_ratio * 0.18)
                + phrase_boost
                + exact_phrase_boost
                + filename_boost
                + intent_boost
            )

            result['direct_overlap'] = direct_overlap
            result['semantic_overlap'] = semantic_overlap
            result['phrase_matches'] = phrase_matches
            result['hybrid_score'] = hybrid_score

            if result['score'] < Config.MIN_VECTOR_SCORE and semantic_overlap == 0 and phrase_matches == 0:
                continue

            effective_hybrid_threshold = Config.MIN_HYBRID_SCORE
            if is_arabic_query:
                effective_hybrid_threshold = min(effective_hybrid_threshold, 0.16)
            if profile['asks_about_types']:
                effective_hybrid_threshold = min(effective_hybrid_threshold, 0.14)
            if hybrid_score < effective_hybrid_threshold:
                continue

            reranked.append(result)

        reranked.sort(
            key=lambda item: (
                item['hybrid_score'],
                item.get('phrase_matches', 0),
                item.get('semantic_overlap', 0),
                item.get('score', 0),
            ),
            reverse=True,
        )
        if not reranked:
            return []

        best_result = reranked[0]
        if query_terms and not is_arabic_query:
            min_overlap = 2 if len(query_terms) >= 3 else 1
            if best_result.get('semantic_overlap', 0) < min_overlap and best_result['score'] < 0.5:
                return []
        elif query_terms and is_arabic_query:
            if (
                best_result['score'] < 0.32
                and best_result.get('semantic_overlap', 0) == 0
                and best_result.get('phrase_matches', 0) == 0
            ):
                return []
        elif best_result['score'] < 0.38:
            return []

        score_floor_base = Config.MIN_HYBRID_SCORE if not is_arabic_query else min(Config.MIN_HYBRID_SCORE, 0.16)
        if profile['asks_about_types']:
            score_floor_base = min(score_floor_base, 0.14)
        score_floor = max(score_floor_base, best_result['hybrid_score'] - 0.16)
        filtered = [item for item in reranked if item['hybrid_score'] >= score_floor]
        return filtered[:top_k]

    def _keyword_search(self, profile, allowed_sources=None, top_k=10):
        query_terms = profile['query_terms']
        semantic_terms = profile['semantic_terms']
        normalized_query = profile['normalized_query']
        boost_phrases = profile['boost_phrases']

        if not semantic_terms and not normalized_query:
            return []

        allowed = set(allowed_sources or [])
        matches = []

        for meta in self.vector_store.metadata:
            if allowed and meta.get('source_file') not in allowed:
                continue

            text = meta.get('text', '')
            normalized_text = self._normalize_text(text)
            text_terms = self._tokenize(text)

            direct_overlap = len(query_terms & text_terms)
            semantic_overlap = len(semantic_terms & text_terms)
            phrase_matches = sum(1 for phrase in boost_phrases if self._normalize_text(phrase) in normalized_text)

            if semantic_terms and semantic_overlap == 0 and phrase_matches == 0 and normalized_query not in normalized_text:
                continue

            overlap_denominator = max(len(query_terms), len(semantic_terms), 1)
            overlap_ratio = semantic_overlap / overlap_denominator
            phrase_boost = min(phrase_matches * 0.09, 0.3)
            direct_boost = 0.06 if direct_overlap > 0 else 0.0
            intent_boost = self._intent_boost(profile, normalized_text)
            score = 0.28 + (overlap_ratio * 0.3) + phrase_boost + direct_boost + intent_boost

            matches.append({
                'text': text,
                'score': score,
                'source_file': meta['source_file'],
                'chunk_id': meta['chunk_id'],
                'chunk_index': meta.get('chunk_index', 0),
                'document_type': meta.get('document_type', 'text'),
                'direct_overlap': direct_overlap,
                'semantic_overlap': semantic_overlap,
                'phrase_matches': phrase_matches,
                'keyword_only': True,
            })

        matches.sort(
            key=lambda item: (
                item.get('phrase_matches', 0),
                item.get('semantic_overlap', 0),
                item.get('direct_overlap', 0),
                item['score'],
            ),
            reverse=True,
        )
        return matches[:top_k]

    def _merge_candidate_results(self, vector_results, keyword_results, top_k):
        merged = {}

        for result in vector_results + keyword_results:
            chunk_id = result['chunk_id']
            existing = merged.get(chunk_id)
            if not existing:
                merged[chunk_id] = dict(result)
                continue

            existing['score'] = max(existing.get('score', 0), result.get('score', 0))
            existing['direct_overlap'] = max(existing.get('direct_overlap', 0), result.get('direct_overlap', 0))
            existing['semantic_overlap'] = max(existing.get('semantic_overlap', 0), result.get('semantic_overlap', 0))
            existing['phrase_matches'] = max(existing.get('phrase_matches', 0), result.get('phrase_matches', 0))
            if result.get('keyword_only'):
                existing['keyword_only'] = True
            if result.get('document_type'):
                existing['document_type'] = result['document_type']
            if result.get('text') and len(result['text']) > len(existing.get('text', '')):
                existing['text'] = result['text']

        merged_results = list(merged.values())
        merged_results.sort(
            key=lambda item: (
                item.get('phrase_matches', 0),
                item.get('semantic_overlap', 0),
                item.get('score', 0),
            ),
            reverse=True,
        )
        return merged_results[:top_k]

    def _intent_boost(self, profile, normalized_text):
        boost = 0.0

        if profile['asks_for_steps'] and 'خطوات التسجيل' in normalized_text:
            boost += 0.18
        if profile['asks_about_registration'] and ('تسجيل الشرك' in normalized_text or 'تسجيل شرك' in normalized_text):
            boost += 0.12
        if profile['asks_about_requirements'] and any(
            phrase in normalized_text
            for phrase in ('الوثائق التاليه', 'الوثائق التالية', 'الاوراق المطلوبه', 'المستندات المطلوبه', 'نسخ من')
        ):
            boost += 0.1
        if profile['asks_about_types'] and any(
            phrase in normalized_text
            for phrase in (
                'الشكل القانوني',
                'الاشكال القانونيه',
                'الأشكال القانونية',
                'شهاده تسجيل التاجر',
                'شركة عاديه عامه',
                'شركة عاديه محدوده',
                'شركة مساهمه خصوصيه',
                'شركة مدنيه',
            )
        ):
            boost += 0.2
        if profile['asks_about_types'] and 'ما هو الشكل القانوني المناسب لعملك' in normalized_text:
            boost += 0.12

        return boost

    def _tokenize(self, text):
        normalized = self._normalize_text(text)
        latin_terms = re.findall(r'[a-zA-Z0-9_.-]+', normalized)
        arabic_terms = re.findall(r'[\u0621-\u064A]{2,}', normalized)

        latin_set = {
            term for term in latin_terms
            if len(term) > 1 and term not in self.STOPWORDS
        }
        arabic_set = set()
        for term in arabic_terms:
            if len(term) <= 1 or term in self.ARABIC_STOPWORDS:
                continue
            arabic_set.add(term)
            simplified = self._normalize_arabic_token(term)
            if len(simplified) > 1 and simplified not in self.ARABIC_STOPWORDS:
                arabic_set.add(simplified)
        return latin_set | arabic_set

    def _normalize_text(self, text):
        value = (text or '').lower()
        value = value.replace('\u0640', '')
        value = re.sub(r'[\u064b-\u065f\u0670]', '', value)
        value = value.replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا')
        value = value.replace('ى', 'ي').replace('ة', 'ه').replace('ؤ', 'و').replace('ئ', 'ي')
        value = re.sub(r'\s+', ' ', value)
        return value.strip()

    def _normalize_arabic_token(self, token):
        value = token
        if value.startswith('ال') and len(value) > 4:
            value = value[2:]
        for suffix in ('يات', 'ات', 'ون', 'ين', 'ان', 'يه', 'ية', 'ه', 'ة'):
            if value.endswith(suffix) and len(value) - len(suffix) >= 3:
                value = value[:-len(suffix)]
                break
        return value
