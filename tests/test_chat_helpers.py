import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from routes.chat import (
    FALLBACK_ANSWER_AR,
    answer_uses_fallback,
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


if __name__ == '__main__':
    unittest.main()
