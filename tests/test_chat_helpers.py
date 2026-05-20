import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from routes.chat import (
    FALLBACK_ANSWER_AR,
    answer_uses_fallback,
    extract_definition_answer,
    extract_definition_term,
    finalize_answer,
    should_retry_with_rescue,
    strip_fallback_from_answer,
)


class TestChatHelpers(unittest.TestCase):
    def test_strip_fallback_from_answer_removes_appended_fallback(self):
        answer = (
            "يتم تسجيل المتجر الإلكتروني ضمن سجل التجارة الإلكترونية.\n\n"
            + FALLBACK_ANSWER_AR
        )
        cleaned = strip_fallback_from_answer(answer, FALLBACK_ANSWER_AR)
        self.assertEqual(
            cleaned,
            "يتم تسجيل المتجر الإلكتروني ضمن سجل التجارة الإلكترونية.",
        )

    def test_answer_uses_fallback_detects_embedded_fallback(self):
        answer = "مقدمة قصيرة. " + FALLBACK_ANSWER_AR
        self.assertTrue(answer_uses_fallback(answer, FALLBACK_ANSWER_AR))

    def test_should_retry_with_rescue_when_sources_exist_and_fallback_present(self):
        sources = [{'filename': '2025.pdf', 'chunk_id': '1', 'score': 0.9}]
        self.assertTrue(
            should_retry_with_rescue(FALLBACK_ANSWER_AR, FALLBACK_ANSWER_AR, sources)
        )

    def test_finalize_answer_prefers_cleaned_answer_when_sources_exist(self):
        sources = [{'filename': '2025.pdf', 'chunk_id': '1', 'score': 0.9}]
        answer = "جواب مدعوم.\n" + FALLBACK_ANSWER_AR
        self.assertEqual(finalize_answer(answer, FALLBACK_ANSWER_AR, sources), "جواب مدعوم.")

    def test_extract_definition_term_from_arabic_question(self):
        self.assertEqual(
            extract_definition_term("ما تعريف المتجر الإلكتروني؟"),
            "المتجر الإلكتروني",
        )

    def test_extract_definition_answer_handles_reversed_pdf_label_pattern(self):
        context = (
            "Reference excerpt 1:\n"
            "المنصة الإلكترونية أو التطبيق الذي يتيح للمزود الإلكتروني تسويق وترويج المتجر الإلكتروني: "
            "وبيع المنتج أو الخدمة أو الإعلان عنهما أو تبادل البيانات الخاصة بهما.\n"
        )
        answer = extract_definition_answer("ما تعريف المتجر الإلكتروني؟", context, "ar")
        self.assertIn("تعريف المتجر الإلكتروني هو:", answer)
        self.assertIn("المنصة الإلكترونية أو التطبيق", answer)
        self.assertIn("وبيع المنتج أو الخدمة", answer)

    def test_extract_definition_answer_accepts_spelling_variant_without_hamza(self):
        context = (
            "Reference excerpt 1:\n"
            "المنصة الإلكترونية أو التطبيق الذي يتيح للمزود الإلكتروني تسويق وترويج المتجر الإلكتروني: "
            "وبيع المنتج أو الخدمة أو الإعلان عنهما أو تبادل البيانات الخاصة بهما.\n"
        )
        answer = extract_definition_answer("تعريف المتجر الالكتروني", context, "ar")
        self.assertIn("تعريف المتجر الالكتروني هو:", answer)
        self.assertIn("المنصة الإلكترونية أو التطبيق", answer)


if __name__ == '__main__':
    unittest.main()
