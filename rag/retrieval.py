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
        'الى', 'إلى', 'الى', 'في', 'من', 'على', 'عن', 'ما', 'ماذا', 'كيف', 'هل',
        'هذا', 'هذه', 'ذلك', 'تلك', 'هناك', 'هنا', 'ثم', 'او', 'أو', 'و', 'يا',
        'تم', 'يتم', 'هي', 'هو', 'هم', 'هن', 'كما', 'كل', 'أي', 'اي', 'لم', 'لن',
        'قد', 'لقد', 'إن', 'ان', 'اذا', 'إذا', 'بعد', 'قبل', 'مع', 'ضمن', 'حول',
        'عند', 'لدى', 'بين', 'حتى', 'إلى', 'الى', 'كان', 'كانت', 'يكون', 'تكون',
    }
    ARABIC_CHAR_PATTERN = re.compile(r'[\u0600-\u06FF]')

    INTENT_SYNONYMS = {
        'goals': {
            'ar': (
                'اهداف', 'أهداف', 'هدف', 'الهدف', 'غاية', 'الغاية', 'غرض',
                'أغراض', 'فوائد', 'مزايا', 'اهمية', 'أهمية', 'يهدف', 'لماذا',
            ),
            'en': (
                'goal', 'goals', 'objective', 'objectives', 'purpose', 'purposes',
                'benefit', 'benefits', 'advantage', 'advantages', 'why',
            ),
        },
        'requirements': {
            'ar': (
                'مستندات', 'المستندات', 'وثائق', 'الوثائق', 'أوراق', 'اوراق',
                'متطلبات', 'الشروط', 'شروط', 'يلزم', 'اللازم', 'المطلوب',
            ),
            'en': (
                'document', 'documents', 'requirements', 'required', 'paperwork',
                'conditions', 'eligibility',
            ),
        },
        'steps': {
            'ar': (
                'خطوات', 'إجراءات', 'اجراءات', 'طريقة', 'طريقه', 'كيفية', 'كيف',
                'انشاء', 'إنشاء', 'بدء', 'تأسيس', 'تاسيس',
            ),
            'en': (
                'steps', 'procedure', 'procedures', 'process', 'how', 'create',
                'start', 'register', 'setup',
            ),
        },
        'types': {
            'ar': (
                'أنواع', 'انواع', 'نوع', 'أشكال', 'اشكال', 'تصنيفات',
                'الشكل القانوني', 'شكل قانوني',
            ),
            'en': (
                'types', 'type', 'categories', 'forms', 'legal form',
                'legal structure',
            ),
        },
        'definitions': {
            'ar': ('تعريف', 'ماهو', 'ما هو', 'ماهي', 'ما هي', 'يعني'),
            'en': ('definition', 'define', 'meaning', 'what is'),
        },
    }

    def __init__(self):
        self.vector_store = VectorStore()

    def retrieve(self, query, top_k=None, allowed_sources=None):
        top_k = top_k or Config.TOP_K
        logger.info("Retrieving top-%s chunks for query", top_k)

        profile = self._build_query_profile(query)
        candidate_count = max(top_k, getattr(Config, 'SEARCH_CANDIDATES', top_k))

        vector_results = self._vector_search(profile, candidate_count, allowed_sources)
        keyword_results = self._keyword_search(
            profile,
            allowed_sources=allowed_sources,
            top_k=candidate_count,
        )
        results = self._merge_candidate_results(
            vector_results,
            keyword_results,
            top_k=candidate_count,
        )
        results = self._rerank_results(profile, results, top_k)

        if not results:
            logger.info("No relevant chunks found")
            return '', []

        results = self._expand_with_neighbors(results, profile, allowed_sources=allowed_sources)
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

        asks_for_steps = self._matches_intent(normalized_query, 'steps')
        asks_about_registration = (
            'تسجيل' in normalized_query
            and any(token in normalized_query for token in ('شرك', 'تاجر', 'مؤسس', 'مؤسسه', 'منش'))
        )
        asks_about_requirements = self._matches_intent(normalized_query, 'requirements')
        asks_about_types = (
            self._matches_intent(normalized_query, 'types')
            and any(token in normalized_query for token in ('شرك', 'مشروع', 'تاجر', 'عملك'))
        )
        asks_about_goals = self._matches_intent(normalized_query, 'goals')
        asks_about_definitions = self._matches_intent(normalized_query, 'definitions')

        mentions_ecommerce = any(
            phrase in normalized_query
            for phrase in (
                'التجاره الالكترونيه',
                'تجاره الكترونيه',
                'متجر الكتروني',
                'المتجر الالكتروني',
                'بيع الكتروني',
                'التسوق الالكتروني',
            )
        )
        mentions_company = any(
            phrase in normalized_query
            for phrase in ('شركه', 'الشركه', 'الشركات', 'مؤسسه', 'المنشاه', 'منشاه', 'تاجر')
        )

        boost_phrases = []
        boost_phrases.extend(self._generic_intent_phrases(asks_about_goals, asks_for_steps, asks_about_requirements, asks_about_types, asks_about_definitions))

        if mentions_ecommerce:
            boost_phrases.extend([
                'التجارة الإلكترونية',
                'المتجر الإلكتروني',
                'سجل التجارة الإلكترونية',
                'المزود الإلكتروني',
                'المستهلك الإلكتروني',
                'العقد الإلكتروني',
            ])

        if asks_about_goals and mentions_ecommerce:
            boost_phrases.extend([
                'الأهداف',
                'يهدف هذا القرار بقانون إلى تحقيق الآتي',
                'تنظيم وضبط التجارة الإلكترونية',
                'حماية أطراف المعاملة الإلكترونية التجارية من الغش والتضليل والخداع',
                'تعزيز ثقة المستهلك بالتجارة الإلكترونية',
                'تشجيع الاستثمار والريادة في مجال الاقتصاد الرقمي والتجارة الإلكترونية',
                'المساهمة في تحقيق التنمية الاقتصادية المستدامة',
            ])

        if asks_for_steps:
            boost_phrases.extend([
                'خطوات التسجيل',
                'إجراءات التسجيل',
                'طريقة التسجيل',
                'كيفية التسجيل',
            ])

        if asks_about_registration:
            boost_phrases.extend([
                'تسجيل الشركة',
                'وزارة الاقتصاد الوطني',
                'مركز خدمات الجمهور',
                'حجز اسم للشركة',
            ])

        if asks_about_requirements:
            boost_phrases.extend([
                'الوثائق التالية',
                'الأوراق المطلوبة',
                'المستندات المطلوبة',
                'نسخ من',
            ])

        if asks_about_types:
            boost_phrases.extend([
                'الشكل القانوني',
                'الأشكال القانونية',
                'ما هو الشكل القانوني المناسب لعملك',
                'شهادة تسجيل التاجر',
                'شركة عادية عامة',
                'شركة عادية محدودة',
                'شركة مساهمة خصوصية',
                'شركة مدنية',
            ])

        if mentions_company:
            boost_phrases.extend([
                'الشركات',
                'تسجيل الشركة',
                'ترخيص المشاريع الصغيرة والمتوسطة',
            ])

        if mentions_ecommerce and asks_for_steps:
            boost_phrases.extend([
                'إنشاء متجر إلكتروني',
                'تسجيل المتجر الإلكتروني',
                'التزامات المزود الإلكتروني',
            ])

        semantic_terms = set(query_terms)
        for phrase in boost_phrases:
            semantic_terms.update(self._tokenize(phrase))

        vector_queries = [query]
        compact_terms = sorted(semantic_terms, key=len, reverse=True)
        if compact_terms:
            vector_queries.append(' '.join(compact_terms[:16]))
        if boost_phrases:
            vector_queries.append(' '.join(boost_phrases[:10]))
        if asks_about_goals and mentions_ecommerce:
            vector_queries.append(
                'أهداف التجارة الإلكترونية تنظيم وضبط التجارة الإلكترونية حماية المستهلك تعزيز الثقة تشجيع الاستثمار'
            )
        if asks_about_types:
            vector_queries.append(
                'أنواع الشركات الأشكال القانونية الشكل القانوني شهادة تسجيل التاجر شركة عادية عامة شركة عادية محدودة شركة مساهمة خصوصية شركة مدنية'
            )
        if asks_about_requirements and mentions_company:
            vector_queries.append(
                'المستندات المطلوبة لتسجيل الشركة الوثائق المطلوبة وزارة الاقتصاد الوطني مركز خدمات الجمهور'
            )

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
            'boost_phrases': self._dedupe_phrases(boost_phrases),
            'vector_queries': deduped_vector_queries,
            'is_arabic_query': is_arabic_query,
            'asks_for_steps': asks_for_steps,
            'asks_about_registration': asks_about_registration,
            'asks_about_requirements': asks_about_requirements,
            'asks_about_types': asks_about_types,
            'asks_about_goals': asks_about_goals,
            'asks_about_definitions': asks_about_definitions,
            'mentions_ecommerce': mentions_ecommerce,
            'mentions_company': mentions_company,
        }

    def _vector_search(self, profile, candidate_count, allowed_sources=None):
        merged = {}

        for idx, vector_query in enumerate(profile['vector_queries']):
            weight = 1.0 if idx == 0 else 0.94
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
            heading_text = normalized_text[:320]
            text_terms = self._tokenize(result['text'])

            direct_overlap = len(query_terms & text_terms)
            semantic_overlap = len(semantic_terms & text_terms)
            substring_hits = sum(
                1 for term in semantic_terms
                if len(term) >= 4 and term in normalized_text
            )
            overlap_denominator = max(len(query_terms), len(semantic_terms), 1)
            overlap_ratio = max(semantic_overlap, substring_hits) / overlap_denominator

            phrase_matches = sum(
                1 for phrase in boost_phrases
                if self._normalize_text(phrase) in normalized_text
            )
            heading_phrase_matches = sum(
                1 for phrase in boost_phrases
                if self._normalize_text(phrase) in heading_text
            )

            phrase_boost = min(phrase_matches * 0.06, 0.30)
            heading_boost = min(heading_phrase_matches * 0.08, 0.26)
            exact_phrase_boost = 0.1 if normalized_query and normalized_query in normalized_text else 0.0
            filename_boost = 0.05 if any(term in self._normalize_text(result['source_file']) for term in query_terms) else 0.0
            intent_boost = self._intent_boost(profile, normalized_text, heading_text)

            hybrid_score = (
                (result['score'] * 0.44)
                + (overlap_ratio * 0.18)
                + (min(direct_overlap, 4) * 0.035)
                + phrase_boost
                + heading_boost
                + exact_phrase_boost
                + filename_boost
                + intent_boost
            )

            result['direct_overlap'] = direct_overlap
            result['semantic_overlap'] = semantic_overlap
            result['substring_hits'] = substring_hits
            result['phrase_matches'] = phrase_matches
            result['heading_phrase_matches'] = heading_phrase_matches
            result['hybrid_score'] = hybrid_score

            if result['score'] < Config.MIN_VECTOR_SCORE and semantic_overlap == 0 and phrase_matches == 0 and substring_hits == 0:
                continue

            effective_hybrid_threshold = Config.MIN_HYBRID_SCORE
            if is_arabic_query:
                effective_hybrid_threshold = min(effective_hybrid_threshold, 0.17)
            if profile['asks_about_types'] or profile['asks_about_goals']:
                effective_hybrid_threshold = min(effective_hybrid_threshold, 0.14)
            if hybrid_score < effective_hybrid_threshold:
                continue

            reranked.append(result)

        reranked.sort(
            key=lambda item: (
                item['hybrid_score'],
                item.get('heading_phrase_matches', 0),
                item.get('phrase_matches', 0),
                item.get('semantic_overlap', 0),
                item.get('substring_hits', 0),
                item.get('score', 0),
            ),
            reverse=True,
        )
        if not reranked:
            return []

        best_result = reranked[0]
        if query_terms and not is_arabic_query:
            min_overlap = 2 if len(query_terms) >= 3 else 1
            if best_result.get('semantic_overlap', 0) < min_overlap and best_result.get('substring_hits', 0) == 0 and best_result['score'] < 0.5:
                return []
        elif query_terms and is_arabic_query:
            if (
                best_result['score'] < 0.28
                and best_result.get('semantic_overlap', 0) == 0
                and best_result.get('phrase_matches', 0) == 0
                and best_result.get('substring_hits', 0) == 0
            ):
                return []
        elif best_result['score'] < 0.35:
            return []

        score_floor_base = Config.MIN_HYBRID_SCORE if not is_arabic_query else min(Config.MIN_HYBRID_SCORE, 0.17)
        if profile['asks_about_types'] or profile['asks_about_goals']:
            score_floor_base = min(score_floor_base, 0.14)
        score_floor = max(score_floor_base, best_result['hybrid_score'] - 0.18)
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
            heading_text = normalized_text[:320]
            text_terms = self._tokenize(text)

            direct_overlap = len(query_terms & text_terms)
            semantic_overlap = len(semantic_terms & text_terms)
            substring_hits = sum(
                1 for term in semantic_terms
                if len(term) >= 4 and term in normalized_text
            )
            phrase_matches = sum(
                1 for phrase in boost_phrases
                if self._normalize_text(phrase) in normalized_text
            )
            heading_phrase_matches = sum(
                1 for phrase in boost_phrases
                if self._normalize_text(phrase) in heading_text
            )

            if (
                semantic_overlap == 0
                and substring_hits == 0
                and phrase_matches == 0
                and normalized_query not in normalized_text
            ):
                continue

            overlap_denominator = max(len(query_terms), len(semantic_terms), 1)
            overlap_ratio = max(semantic_overlap, substring_hits) / overlap_denominator
            phrase_boost = min(phrase_matches * 0.08, 0.32)
            heading_boost = min(heading_phrase_matches * 0.09, 0.27)
            direct_boost = min(direct_overlap, 4) * 0.04
            intent_boost = self._intent_boost(profile, normalized_text, heading_text)
            score = 0.24 + (overlap_ratio * 0.26) + phrase_boost + heading_boost + direct_boost + intent_boost

            matches.append({
                'text': text,
                'score': score,
                'source_file': meta['source_file'],
                'chunk_id': meta['chunk_id'],
                'chunk_index': meta.get('chunk_index', 0),
                'document_type': meta.get('document_type', 'text'),
                'direct_overlap': direct_overlap,
                'semantic_overlap': semantic_overlap,
                'substring_hits': substring_hits,
                'phrase_matches': phrase_matches,
                'heading_phrase_matches': heading_phrase_matches,
                'keyword_only': True,
            })

        matches.sort(
            key=lambda item: (
                item.get('heading_phrase_matches', 0),
                item.get('phrase_matches', 0),
                item.get('semantic_overlap', 0),
                item.get('substring_hits', 0),
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
            existing['substring_hits'] = max(existing.get('substring_hits', 0), result.get('substring_hits', 0))
            existing['phrase_matches'] = max(existing.get('phrase_matches', 0), result.get('phrase_matches', 0))
            existing['heading_phrase_matches'] = max(existing.get('heading_phrase_matches', 0), result.get('heading_phrase_matches', 0))
            if result.get('keyword_only'):
                existing['keyword_only'] = True
            if result.get('document_type'):
                existing['document_type'] = result['document_type']
            if result.get('text') and len(result['text']) > len(existing.get('text', '')):
                existing['text'] = result['text']

        merged_results = list(merged.values())
        merged_results.sort(
            key=lambda item: (
                item.get('heading_phrase_matches', 0),
                item.get('phrase_matches', 0),
                item.get('semantic_overlap', 0),
                item.get('substring_hits', 0),
                item.get('score', 0),
            ),
            reverse=True,
        )
        return merged_results[:top_k]

    def _expand_with_neighbors(self, results, profile, allowed_sources=None):
        if not results:
            return []

        allowed = set(allowed_sources or [])
        ranked = []
        seen = set()

        def add_result(item):
            chunk_id = item.get('chunk_id')
            if not chunk_id or chunk_id in seen:
                return
            if allowed and item.get('source_file') not in allowed:
                return
            seen.add(chunk_id)
            ranked.append(item)

        for result in results:
            add_result(result)

        if not (
            profile['asks_for_steps']
            or profile['asks_about_requirements']
            or profile['asks_about_types']
            or profile['asks_about_goals']
        ):
            return ranked

        metadata_by_position = {
            (meta.get('source_file'), meta.get('chunk_index')): meta
            for meta in self.vector_store.metadata
        }

        for result in list(results):
            base_score = result.get('hybrid_score', result.get('score', 0))
            for offset in (-1, 1):
                neighbor_meta = metadata_by_position.get((result.get('source_file'), result.get('chunk_index', 0) + offset))
                if not neighbor_meta:
                    continue
                add_result({
                    'text': neighbor_meta['text'],
                    'score': max(base_score - 0.04, 0.01),
                    'source_file': neighbor_meta['source_file'],
                    'chunk_id': neighbor_meta['chunk_id'],
                    'chunk_index': neighbor_meta.get('chunk_index', 0),
                    'document_type': neighbor_meta.get('document_type', 'text'),
                    'hybrid_score': max(base_score - 0.04, 0.01),
                })

        ranked.sort(
            key=lambda item: (
                item.get('hybrid_score', item.get('score', 0)),
                item.get('score', 0),
            ),
            reverse=True,
        )
        return ranked[: max(Config.TOP_K + 2, len(results))]

    def _intent_boost(self, profile, normalized_text, heading_text):
        boost = 0.0

        if profile['asks_for_steps'] and any(
            phrase in heading_text
            for phrase in ('خطوات التسجيل', 'إجراءات التسجيل', 'طريقة التسجيل', 'كيفية التسجيل')
        ):
            boost += 0.18

        if profile['asks_about_registration'] and any(
            phrase in normalized_text
            for phrase in ('تسجيل الشرك', 'وزارة الاقتصاد الوطني', 'مركز خدمات الجمهور')
        ):
            boost += 0.12

        if profile['asks_about_requirements'] and any(
            phrase in normalized_text
            for phrase in ('الوثائق التاليه', 'الاوراق المطلوبه', 'المستندات المطلوبه', 'نسخ من')
        ):
            boost += 0.11

        if profile['asks_about_types'] and any(
            phrase in heading_text
            for phrase in (
                'الشكل القانوني',
                'الاشكال القانونيه',
                'ما هو الشكل القانوني المناسب لعملك',
                'شهاده تسجيل التاجر',
                'شركه عاديه عامه',
                'شركه عاديه محدوده',
                'شركه مساهمه خصوصيه',
                'شركه مدنيه',
            )
        ):
            boost += 0.20

        if profile['asks_about_goals'] and any(
            phrase in heading_text
            for phrase in (
                'الاهداف',
                'يهدف هذا القرار بقانون',
                'فوائد',
                'مزايا',
                'تنظيم وضبط التجاره الالكترونيه',
            )
        ):
            boost += 0.24

        if profile['mentions_ecommerce'] and any(
            phrase in normalized_text
            for phrase in ('التجاره الالكترونيه', 'المتجر الالكتروني', 'سجل التجاره الالكترونيه')
        ):
            boost += 0.06

        if profile['asks_about_definitions'] and any(
            phrase in heading_text
            for phrase in ('تعاريف', 'التعريفات', 'يقصد به', 'يعني')
        ):
            boost += 0.1

        return boost

    def _matches_intent(self, normalized_query, intent_name):
        synonyms = self.INTENT_SYNONYMS[intent_name]['ar'] + self.INTENT_SYNONYMS[intent_name]['en']
        normalized_synonyms = {self._normalize_text(value) for value in synonyms}
        return any(term and term in normalized_query for term in normalized_synonyms)

    def _generic_intent_phrases(self, asks_about_goals, asks_for_steps, asks_about_requirements, asks_about_types, asks_about_definitions):
        phrases = []
        if asks_about_goals:
            phrases.extend(['الأهداف', 'الهدف', 'الغاية', 'الفوائد', 'المزايا'])
        if asks_for_steps:
            phrases.extend(['الخطوات', 'الإجراءات', 'طريقة', 'كيفية'])
        if asks_about_requirements:
            phrases.extend(['المستندات المطلوبة', 'الوثائق', 'الشروط', 'المتطلبات'])
        if asks_about_types:
            phrases.extend(['الأنواع', 'الأشكال القانونية', 'الشكل القانوني'])
        if asks_about_definitions:
            phrases.extend(['التعريف', 'التعاريف', 'يقصد به'])
        return phrases

    def _dedupe_phrases(self, phrases):
        deduped = []
        seen = set()
        for phrase in phrases:
            normalized_phrase = self._normalize_text(phrase)
            if not normalized_phrase or normalized_phrase in seen:
                continue
            seen.add(normalized_phrase)
            deduped.append(phrase)
        return deduped

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
        value = self._normalize_text(token)
        for prefix in ('وال', 'بال', 'كال', 'فال', 'لل', 'ال'):
            if value.startswith(prefix) and len(value) - len(prefix) >= 3:
                value = value[len(prefix):]
                break
        for suffix in ('يات', 'ات', 'ون', 'ين', 'ان', 'يه', 'ية', 'ها', 'هم', 'كما', 'كم', 'نا', 'ه', 'ة'):
            if value.endswith(suffix) and len(value) - len(suffix) >= 3:
                value = value[:-len(suffix)]
                break
        return value
