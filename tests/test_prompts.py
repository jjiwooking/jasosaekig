import unittest

from modules.prompts import (
    allocation_prompt,
    essay_writer_prompt,
    question_analysis_prompt,
)
from modules.repetition import local_repetition_report


class PromptTests(unittest.TestCase):
    def test_question_analysis_contains_cold_gate_rules(self):
        p = question_analysis_prompt(
            {"id": "q1", "question_text": "협업 경험을 적어주세요", "char_limit": 700},
            {"business_summary": "test"},
            {"core_tasks": ["test"]},
            "AI 업무지원 프로그램을 만든 경험을 말하고 싶다",
            [],
        )
        self.assertIn("정확하고 냉정", p)
        self.assertIn("하드 조건", p)
        self.assertIn("내가 하고 싶은 말", p)
        self.assertIn("AI 업무지원 프로그램", p)

    def test_allocation_has_requirement_gate_and_repeat_block(self):
        p = allocation_prompt(
            [{"id": "q1", "analysis": {"hard_requirements": ["직접 도움"]}}],
            [{"id": "e1", "title": "경험"}],
            {},
            {},
            [],
        )
        self.assertIn("Question Requirement Gate", p)
        self.assertIn("의미가 같으면 같은 소재", p)
        self.assertIn("gap", p)

    def test_writer_preserves_user_message(self):
        p = essay_writer_prompt(
            {"id": "q1", "question_text": "지원 동기", "char_limit": 700},
            {"must_answer_elements": ["동기"]},
            {"requirement_gate": {"status": "pass"}},
            {"title": "AI 프로그램 제작"},
            {}, {}, {}, [],
            "데이터분석과 AI 업무개선 능력을 꼭 보여주고 싶다",
            "", [],
        )
        self.assertIn("반드시 전달하고 싶은 말", p)
        self.assertIn("데이터분석과 AI 업무개선", p)
        self.assertIn("소제목", p)

    def test_local_repetition_report(self):
        r = local_repetition_report("이를 통해 성장했습니다. 이를 통해 확인했습니다.")
        self.assertIn("이를 통해", r["ai_tone_hits"])


if __name__ == "__main__":
    unittest.main()
