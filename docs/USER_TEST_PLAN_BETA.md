# User Test Plan — Observable Beta

## Goal

Test whether 5–10 Chinese tea beginners can complete the comparison/rejudge flow and understand why the system judged as it did. This is a formative usability and value study, not statistical validation.

## Participants

- Drinks or buys Chinese tea occasionally but does not identify as a tea professional.
- Has compared products online before.
- Exclude the project team and people already trained on Guancha’s concepts.
- Assign only a participant ID; do not collect phone, WeChat, real name, or unnecessary demographics.

## Setup

- Use a dedicated test environment and non-sensitive product screenshots.
- Prepare two comparable tea candidates and simulated merchant replies.
- Confirm event logging path, clock, and test build commit before each session.
- Obtain recording/quote consent separately. Analytics never contains screen recordings or verbatim replies.
- Moderator uses the observation template; do not teach Evidence/Interpretation/Decision before the comprehension probe.

## Core task

1. Open Guancha and express the current Need.
2. Add at least two candidate teas with screenshots.
3. Start analysis and inspect the initial result.
4. Explain why the system prioritizes or does not prioritize each candidate.
5. Open merchant questions; decide which, if any, is worth asking.
6. Simulate entering merchant replies.
7. Inspect the unified rejudge and explain what changed or stayed the same.
8. Make a final candidate choice; optionally add it to Tea Stock.

## Moderator protocol

- Ask “What would you do next?” before helping.
- If blocked for 30 seconds, give the smallest navigation hint and mark the step assisted.
- Ask source/comprehension questions before revealing intended meanings.
- Do not praise an answer or imply that asking the merchant is expected.
- Stop if a participant enters real private chat, credentials, or identifying information; replace it with prepared test text.

## Measures

- Step completion: unassisted / assisted / failed.
- Time to Need, first Result, Question, Rejudge, and final choice.
- Ranking comprehension and source-boundary comprehension.
- Confusions, reversals, and error recovery.
- Whether a question is worth asking and why.
- Whether rejudge changes confidence/action.
- Perceived value versus OCR fields and versus general AI screenshot chat.

## Success criteria for the study

The study is successfully executed when every consented session has a complete observation record, telemetry can be reconciled by anonymous session ID, failures are classified, and no result is invented. Product success thresholds are deliberately not preclaimed; use the evidence to decide fix, retest, narrow scope, or stop.

## Stop conditions

- Privacy leak, cross-session data exposure, or real credentials/private chat in logs.
- Decision/Answer contradiction or stale Decision paired with a changed Need.
- Core flow cannot run reliably in the test environment.
- Moderator must repeatedly reconstruct the intended explanation for participants.

## Analysis

Triangulate raw event counts, task observations, comprehension answers, and interview quotes. Report counterexamples and assisted completions. Do not calculate persuasive percentages from a tiny convenience sample without raw numerator/denominator beside them.
