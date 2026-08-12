from __future__ import annotations

import json
import os
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "backend" / "evaluation" / "ai_eval_cases.json"
OUTPUT = ROOT / "artifacts" / "observable-beta" / "AI_EVAL_RESULTS.md"


def run() -> tuple[int, dict[str, str]]:
    cases = json.loads(MANIFEST.read_text(encoding="utf-8"))
    results: dict[str, str] = {}; node_results: dict[str, str] = {}
    environment = os.environ.copy()
    source = str(ROOT / "backend" / "src")
    environment["PYTHONPATH"] = source + (os.pathsep + environment["PYTHONPATH"] if environment.get("PYTHONPATH") else "")
    has_database = bool(environment.get("TEST_DATABASE_URL"))
    for case in cases:
        if case["requires_database"] and not has_database:
            results[case["case_id"]] = "BLOCKED"; continue
        statuses = []
        for nodeid in case["pytest_nodeids"]:
            if nodeid not in node_results:
                completed = subprocess.run(
                    [sys.executable, "-m", "pytest", nodeid, "-q"], cwd=ROOT,
                    env=environment, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                )
                output = completed.stdout.lower()
                node_results[nodeid] = "PASS" if completed.returncode == 0 and " skipped" not in output else "BLOCKED" if completed.returncode == 0 else "FAIL"
            statuses.append(node_results[nodeid])
        results[case["case_id"]] = "FAIL" if "FAIL" in statuses else "BLOCKED" if "BLOCKED" in statuses else "PASS"
    counts = Counter(results.values()); by_category: dict[str, Counter[str]] = {}
    for case in cases:
        by_category.setdefault(case["category"], Counter())[results[case["case_id"]]] += 1
    lines = [
        "# AI Eval Results", "", f"Run at: {datetime.now(timezone.utc).isoformat()}",
        "", "This is the fixed deterministic/fixture test-set result, not real-world model accuracy.",
        "No Provider network call or API key access is performed.", "", "## Totals", "",
        f"- Total: {len(cases)}", f"- PASS: {counts['PASS']}", f"- FAIL: {counts['FAIL']}", f"- BLOCKED: {counts['BLOCKED']}",
        "", "## Cases", "", "| Case | Level | Category | Failure taxonomy | Result |", "|---|---|---|---|---|",
    ]
    for case in cases:
        lines.append(f"| {case['case_id']} | {case['level']} | {case['category']} | {case['failure_category']} | {results[case['case_id']]} |")
    lines.extend(["", "## By category", ""])
    for category, values in sorted(by_category.items()):
        lines.append(f"- {category}: PASS {values['PASS']} / FAIL {values['FAIL']} / BLOCKED {values['BLOCKED']}")
    lines.extend(["", "## Boundary", "", "- BLOCKED means an executable case could not run in this environment; it is never counted as PASS.", "- `fixture_pipeline` starts from fixed structured Extraction fixtures and does not evaluate the live vision Provider.", "- Failure taxonomy is the classification assigned if the case fails; PASS does not mean that a failure occurred.", ""])
    OUTPUT.parent.mkdir(parents=True, exist_ok=True); OUTPUT.write_text("\n".join(lines), encoding="utf-8")
    return (1 if counts["FAIL"] else 0), results


if __name__ == "__main__":
    code, result = run()
    print(f"Total={len(result)} PASS={sum(v == 'PASS' for v in result.values())} FAIL={sum(v == 'FAIL' for v in result.values())} BLOCKED={sum(v == 'BLOCKED' for v in result.values())}")
    raise SystemExit(code)
