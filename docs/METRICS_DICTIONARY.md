# Beta Metrics Dictionary

No metric below has a current observed value. Report raw counts first because the planned sample is 5–10 participants.

| Metric | Operational definition | Source | Guardrail |
|---|---|---|---|
| Started sessions | Unique `anonymous_session_id` with `start_selection`. | Analytics | Per-tab session, not unique person. |
| Need submitted | Unique started sessions reaching `need_submitted`. | Server event | No Need text retained. |
| Candidate ready | Unique started sessions with at least one `candidate_image_added`; observation separately checks ≥2 candidates. | Server event + notes | Upload event is not extraction success. |
| Analysis completed | Unique started sessions with `analysis_completed`. | Server event | Client may not report success. |
| Result examined | Count/sessions with `candidate_result_viewed`. | Client event | Repeat carousel views are legitimate events. |
| Question viewed | Unique sessions with `merchant_question_viewed`. | Client event | Not equivalent to intent. |
| Question copied | Unique sessions with `merchant_question_copied`. | Client event | Copy-all uses `action_bucket=copy_all`. |
| Merchant reply submitted | Unique sessions with server `merchant_reply_submitted`. | Server event | No raw reply in analytics. |
| Merchant reply unusable | Server `merchant_reply_unusable` count by `failure_category` when present. | Server event | Never include parser message/text. |
| Rejudge completed | Unique sessions with `rejudge_completed`. | Server event | Client may not report success. |
| Candidate selected | Unique sessions with `candidate_selected`. | Client event | Represents UI selection, not purchase. |
| Tea stock added | Count by `source` (`selection` or `manual`). | Client event | Not a commerce conversion. |
| Flow abandoned | Explicit active-flow return-home events by `stage`. | Client event | Does not infer tab close/crash. |
| Task completion | Participant completes the scripted final choice without moderator takeover. | Observation | Record assisted vs unassisted. |
| Comprehension | Participant correctly explains ranking basis and uncertainty. | Observation rubric | Not inferred from clicks. |
| Source-boundary accuracy | Correctly identifies product/system/merchant source in probe. | Interview/observation | Ask before explaining. |
| Question-value judgment | Participant says whether they would ask and why. | Interview | Keep verbatim rationale; no leading. |

Any later rate must declare numerator, denominator, unit of analysis, exclusions, and sample size next to the result. Do not call fixed-eval pass rate model accuracy or small-Beta activity statistical significance.
