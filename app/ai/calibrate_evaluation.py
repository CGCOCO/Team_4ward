"""Draw an expert review sample or correct aggregate AI scores offline."""

import argparse
import json
from pathlib import Path
from random import Random
from statistics import mean
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from app.ai.evaluate import RUBRIC_VERSION, Case, Ratings, _digest, _write_report

MeanScore = Annotated[float, Field(strict=True, ge=1, le=5)]


class ExpertMeans(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hazard: MeanScore
    accident: MeanScore
    prevention: MeanScore
    law: MeanScore


class ExpertSample(BaseModel):
    rubric_version: str
    manifest_sha256: str
    population_count: int = Field(gt=1)
    case_ids: list[str]
    means: ExpertMeans
    seed: int | None = None


def draw_sample(manifest: bytes, size: int, seed: int) -> dict:
    cases = TypeAdapter(list[Case]).validate_json(manifest.decode("utf-8-sig"))
    ids = sorted(case.id for case in cases)
    if len(set(ids)) != len(ids):
        raise ValueError("Manifest case IDs must be unique")
    if not 1 <= size < len(ids):
        raise ValueError("Sample size must be positive and smaller than the number of photos")
    return {
        "rubric_version": RUBRIC_VERSION,
        "manifest_sha256": _digest(manifest),
        "population_count": len(ids),
        "seed": seed,
        "case_ids": Random(seed).sample(ids, size),
        "means": {name: None for name in ExpertMeans.model_fields},
    }


def correct_means(report: dict, expert: ExpertSample) -> dict:
    if report.get("rubric_version") != RUBRIC_VERSION or expert.rubric_version != RUBRIC_VERSION:
        raise ValueError(f"Both inputs must use rubric {RUBRIC_VERSION}")
    if report.get("manifest_sha256") != expert.manifest_sha256:
        raise ValueError("Expert sample and AI report must come from the same manifest")

    ai_ratings = {}
    for row in report["cases"]:
        case_id = row["case_id"]
        if case_id in ai_ratings:
            raise ValueError(f"Duplicate AI case ID: {case_id}")
        if "error" in row or "ratings" not in row:
            raise ValueError(f"AI ratings are incomplete for case {case_id}")
        ai_ratings[case_id] = Ratings.model_validate(row["ratings"])

    if len(ai_ratings) != expert.population_count:
        raise ValueError("AI report must contain scores for every photo in the manifest")

    paired_ids = set(expert.case_ids)
    if not paired_ids or len(paired_ids) != len(expert.case_ids):
        raise ValueError("Expert sample must contain unique case IDs")
    if unknown_ids := paired_ids - ai_ratings.keys():
        raise ValueError(f"Expert photos missing from AI report: {', '.join(sorted(unknown_ids))}")
    if len(paired_ids) == len(ai_ratings):
        raise ValueError("Expert sample must be smaller than the AI population")
    if expert.seed is not None:
        drawn_ids = set(Random(expert.seed).sample(sorted(ai_ratings), len(paired_ids)))
        if drawn_ids != paired_ids:
            raise ValueError("Expert IDs do not match the draw from the recorded seed and AI population")

    criteria = {}
    for name, expert_mean in expert.means.model_dump().items():
        scores = {case_id: getattr(ratings, name).score for case_id, ratings in ai_ratings.items()}
        ai_mean = mean(scores.values())
        paired_ai_mean = mean(scores[case_id] for case_id in paired_ids)
        correction = expert_mean - paired_ai_mean
        corrected_mean = ai_mean + correction
        criteria[name] = {
            "ai_mean": ai_mean,
            "paired_ai_mean": paired_ai_mean,
            "expert_sample_mean": expert_mean,
            "correction": correction,
            "corrected_mean": corrected_mean,
            "outside_score_range": not 1 <= corrected_mean <= 5,
        }

    return {
        "method": "finite-population-difference-estimator",
        "rubric_version": RUBRIC_VERSION,
        "manifest_sha256": expert.manifest_sha256,
        "ai_count": len(ai_ratings),
        "expert_count": len(paired_ids),
        "expert_case_ids": expert.case_ids,
        "sample_seed": expert.seed,
        "criteria": criteria,
        "confidence_interval": None,
        "confidence_interval_reason": "Only aggregate expert means were supplied.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    sample = commands.add_parser("sample", help="Draw expert case IDs before reviewing scores")
    sample.add_argument("manifest", type=Path)
    sample.add_argument("--size", type=int, default=20)
    sample.add_argument("--seed", type=int, required=True)
    sample.add_argument("--output", type=Path, required=True)
    correct = commands.add_parser("correct", help="Apply the expert mean correction to each criterion")
    correct.add_argument("report", type=Path)
    correct.add_argument("expert_sample", type=Path)
    correct.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if args.output.exists():
        parser.error("--output must be a new file")
    try:
        if args.command == "sample":
            result = draw_sample(args.manifest.read_bytes(), args.size, args.seed)
        else:
            report = args.report.read_bytes()
            expert = args.expert_sample.read_bytes()
            result = correct_means(
                json.loads(report.decode("utf-8-sig")),
                ExpertSample.model_validate_json(expert.decode("utf-8-sig")),
            )
            result["ai_report_sha256"] = _digest(report)
            result["expert_sample_sha256"] = _digest(expert)
        _write_report(args.output, result)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
