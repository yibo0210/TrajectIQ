"""Create one Dashboard-ready artifact from TrajectIQ evaluation results."""

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from .attribution import attribute_regressions
from .gate import evaluate_gate, load_gate_config
from .regression import compare_versions
from .run import VERSIONS


def build_dashboard_data(*, baseline_name: str, candidate_name: str, gate_config: Path) -> dict[str, object]:
    """Bundle report, diagnosis, and gate results for the standalone Dashboard."""
    baseline = VERSIONS[baseline_name]
    candidate = VERSIONS[candidate_name]
    report = compare_versions(baseline=baseline, candidate=candidate)
    gate = evaluate_gate(report=report, config=load_gate_config(gate_config))
    diagnoses = attribute_regressions(baseline=baseline, candidate=candidate)
    return {
        "report": report.to_dict(),
        "diagnoses": [asdict(diagnosis) for diagnosis in diagnoses],
        "gate": gate.to_dict(),
    }


def main() -> None:
    """Write a single JSON artifact for the TrajectIQ Dashboard."""
    parser = argparse.ArgumentParser(description="Build a Dashboard-ready TrajectIQ report")
    parser.add_argument("--baseline", choices=VERSIONS, default="baseline")
    parser.add_argument("--candidate", choices=VERSIONS, default="regression")
    parser.add_argument("--config", type=Path, default=Path("release-gate.yaml"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = build_dashboard_data(
        baseline_name=args.baseline,
        candidate_name=args.candidate,
        gate_config=args.config,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
