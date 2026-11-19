from pathlib import Path
from unittest import TestCase

from app.ai.evaluate import (
    AnalysisResult,
    Case,
    Judgment,
    RetrievalTrace,
    _count_metrics,
    _prepare,
    _references,
    _validate_judgment,
)


class PhotoEvaluationTest(TestCase):
    def setUp(self):
        self.case = Case(
            id="excavator",
            image=Path("excavator.jpg"),
            expected_hazards=[{"text": "굴착기 전도 위험", "critical": True}],
            expected_law_ids=["007363-199", "007363-221-2"],
        )
        result = AnalysisResult(
            hazards=["굴착기 충돌 위험"],
            accidents=[],
            preventions=[],
            related_laws=[{"article": "제221조의2(충돌위험 방지조치)", "content": "후방 확인"}],
        )
        self.items, self.expected, self.sources = _prepare(
            self.case, result, _references(self.case.expected_law_ids)
        )
        self.judgment = Judgment.model_validate({
            "checks": [
                {"item_id": "hazards-1", "verdict": "supported", "severity": "normal",
                 "reason": "사진에서 볼 수 있는 위험", "source_id": "", "quote": ""},
                {"item_id": "laws-1", "verdict": "supported", "severity": "normal",
                 "reason": "인용 근거 확인", "source_id": "007363-221-2",
                 "quote": "굴착기에 사람이 부딪히는 것을 방지하기 위해"},
            ],
            "coverage": [
                {"hazard_id": "required-1", "verdict": "missed", "matched_item_ids": [],
                 "reason": "전도 위험이 결과에 빠짐"},
            ],
        })

    def validate(self):
        return _validate_judgment(self.judgment, self.items, self.expected, self.sources)

    def test_verified_quotation_and_branched_article(self):
        law = self.validate()[1]
        self.assertTrue(law["quote_verified"])
        self.assertEqual(law["verdict"], "supported")

    def test_invented_or_wrong_source_quote_does_not_pass(self):
        law = self.judgment.checks[1]
        law.quote = "원문에 없는 인용"
        self.assertEqual(self.validate()[1]["verdict"], "insufficient_reference")
        law.source_id = "007363-199"
        law.quote = "그 기계가 넘어지거나 굴러떨어짐으로써"
        self.assertEqual(self.validate()[1]["verdict"], "insufficient_reference")

    def test_missing_judge_item_is_rejected(self):
        self.judgment.checks.pop()
        with self.assertRaisesRegex(ValueError, "one verdict per analysis item"):
            self.validate()

    def test_search_recall_requires_trace_and_does_not_use_final_citations(self):
        findings = self.validate()
        metrics, misses, _ = _count_metrics(
            self.case, self.items, self.expected, self.judgment, findings, None
        )
        self.assertIsNone(metrics["candidate_law_recall"]["rate"])
        self.assertEqual(misses, ["required-1"])
        trace = RetrievalTrace(candidates=["007363-199"], reranked=[])
        metrics, _, _ = _count_metrics(
            self.case, self.items, self.expected, self.judgment, findings, trace
        )
        self.assertEqual(metrics["candidate_law_recall"]["rate"], 0.5)
        self.assertEqual(metrics["reranked_law_recall"]["rate"], 0)

    def test_judge_abstention_does_not_reduce_the_reference_denominator(self):
        self.judgment.coverage[0].verdict = "not_verifiable"
        metrics, misses, _ = _count_metrics(
            self.case, self.items, self.expected, self.judgment, self.validate(), None
        )
        self.assertEqual(metrics["expected_hazard_recall"]["total"], 1)
        self.assertEqual(metrics["expected_hazard_recall"]["rate"], 0)
        self.assertEqual(metrics["expected_hazards_not_verifiable"]["count"], 1)
        self.assertEqual(misses, [])
