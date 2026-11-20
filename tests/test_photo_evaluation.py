import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock

from app.ai.calibrate_evaluation import ExpertSample, correct_means, draw_sample

from app.ai.evaluate import (
    AnalysisResult,
    Case,
    Judgment,
    Ratings,
    RetrievalTrace,
    _count_metrics,
    _prepare,
    _references,
    _summary,
    _validate_judgment,
    evaluate_case,
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

    def test_single_judge_call_returns_checks_and_four_ratings(self):
        payload = self.judgment.model_dump()
        payload["ratings"] = _ratings(4)
        client = Mock()
        client.models.generate_content.return_value = SimpleNamespace(
            text=json.dumps(payload), model_version="test-model", usage_metadata=None,
        )
        with TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / self.case.image).write_bytes(b"mock image input")
            self.case.result = Path("analysis.json")
            (folder / self.case.result).write_text(json.dumps({
                "hazards": ["굴착기 충돌 위험"], "accidents": [], "preventions": [],
                "related_laws": [{"article": "제221조의2(충돌위험 방지조치)", "content": "후방 확인"}],
            }), encoding="utf-8")
            row = evaluate_case(self.case, folder, client, "test-model", False, score=True)
            self.assertEqual(row["ratings"], _ratings(4))
            self.assertTrue(row["checks"][1]["quote_verified"])
            self.assertEqual(_summary([row])["ratings"]["law"], {"mean": 4, "count": 1})
            client.models.generate_content.assert_called_once()

            payload["ratings"]["law"]["score"] = 6
            client.models.generate_content.return_value.text = json.dumps(payload)
            with self.assertRaisesRegex(ValueError, "Score must be between 1 and 5"):
                evaluate_case(self.case, folder, client, "test-model", False, score=True)


def _ratings(score):
    return {name: {"score": score, "reason": "채점 근거"} for name in Ratings.model_fields}


class MeanCorrectionTest(TestCase):
    def setUp(self):
        manifest = json.dumps([
            {"id": f"photo-{index}", "image": f"{index}.jpg"} for index in range(100)
        ]).encode()
        self.sample = draw_sample(manifest, 20, 42)
        self.sample["means"] = {name: 3.9 for name in Ratings.model_fields}
        paired = self.sample["case_ids"]
        rest = sorted(set(f"photo-{index}" for index in range(100)) - set(paired))
        self.report = {
            "manifest_sha256": self.sample["manifest_sha256"],
            "rubric_version": self.sample["rubric_version"],
            "cases": [
                {"case_id": case_id, "ratings": _ratings(5 if index < high_count else 4)}
                for group, high_count in ((paired, 2), (rest, 16))
                for index, case_id in enumerate(group)
            ],
        }

    def test_corrects_whole_population_with_paired_mean_difference(self):
        corrected = correct_means(self.report, ExpertSample.model_validate(self.sample))
        self.assertEqual(corrected["ai_count"], 100)
        self.assertEqual(corrected["expert_count"], 20)
        self.assertIsNone(corrected["confidence_interval"])
        row = corrected["criteria"]["hazard"]
        self.assertAlmostEqual(row["ai_mean"], 4.18)
        self.assertAlmostEqual(row["paired_ai_mean"], 4.10)
        self.assertAlmostEqual(row["correction"], -0.20)
        self.assertAlmostEqual(row["corrected_mean"], 3.98)

    def test_incomplete_population_is_rejected(self):
        self.report["cases"].pop()
        with self.assertRaisesRegex(ValueError, "every photo"):
            correct_means(self.report, ExpertSample.model_validate(self.sample))

    def test_expert_sample_id_cannot_be_swapped_after_drawing(self):
        self.sample["case_ids"][0] = self.report["cases"][-1]["case_id"]
        with self.assertRaisesRegex(ValueError, "do not match the draw"):
            correct_means(self.report, ExpertSample.model_validate(self.sample))
