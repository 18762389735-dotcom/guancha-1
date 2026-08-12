from __future__ import annotations

import json
from pathlib import Path

from guancha_api.product_events import FailureCategory


def test_ai_eval_manifest_has_27_closed_cases_and_real_nodeids() -> None:
    root = Path(__file__).resolve().parents[2]
    cases = json.loads((root / "backend/evaluation/ai_eval_cases.json").read_text(encoding="utf-8"))
    assert len(cases) == 27
    assert len({case["case_id"] for case in cases}) == 27
    allowed = set(FailureCategory.__args__)
    assert all(case["failure_category"] in allowed for case in cases)
    assert all(case["pytest_nodeids"] for case in cases)
    assert all((root / nodeid.split("::", 1)[0]).is_file() for case in cases for nodeid in case["pytest_nodeids"])
    assert all(case["level"] in {"deterministic_unit", "fixture_pipeline", "database_integration"} for case in cases)
