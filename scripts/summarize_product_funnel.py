from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from pathlib import Path

from export_product_events import read_events


STAGES = (
    ("START", {"start_selection"}),
    ("NEED SUBMITTED", {"need_submitted"}),
    ("CANDIDATE READY", {"candidate_image_added"}),
    ("ANALYSIS COMPLETED", {"analysis_completed"}),
    ("QUESTION ENGAGED", {"merchant_question_viewed", "merchant_question_copied"}),
    ("MERCHANT REPLY", {"merchant_reply_submitted"}),
    ("REJUDGE COMPLETED", {"rejudge_completed"}),
    ("CANDIDATE SELECTED", {"candidate_selected"}),
)


def summarize(path: Path) -> str:
    rows = read_events(path); events = Counter(str(row["event_name"]) for row in rows)
    sessions = {str(row["anonymous_session_id"]) for row in rows if row.get("anonymous_session_id")}
    by_session: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        if row.get("anonymous_session_id"):
            by_session[str(row["anonymous_session_id"])].add(str(row["event_name"]))
    lines = ["Raw activity summary (not statistical significance or a conversion-rate claim)", f"event_count={len(rows)}", f"unique_session_count={len(sessions)}", "events:"]
    lines.extend(f"  {name}={count}" for name, count in sorted(events.items()))
    lines.append("stage_progression_raw_unique_sessions:")
    reached_previous = set(by_session)
    for label, names in STAGES:
        reached = {session for session in reached_previous if by_session[session] & names}
        lines.append(f"  {label}={len(reached)}")
        reached_previous = reached
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize raw Guancha funnel activity.")
    parser.add_argument("source", type=Path); args = parser.parse_args()
    print(summarize(args.source)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
