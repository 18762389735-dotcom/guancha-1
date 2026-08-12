# Beta Metrics Dictionary

No metric below has a current observed value. Report raw counts first for a future 5–10 participant study. No North Star metric is defined.

## Selection Start

- **Definition:** Count of distinct analytics sessions that emit `start_selection` during a declared study window.
- **Event:** Client `start_selection`.
- **Denominator:** None for the raw count. If a future start rate is calculated, the denominator must be distinct study sessions with `app_open` in the same window.
- **Interpretation:** A participant entered the selection flow; it does not show that a Need or candidate was submitted.
- **Limitation:** `anonymous_session_id` is per tab/sessionStorage, not a unique person. Refresh and multi-tab behavior require study notes.

## Analysis Completion

- **Definition:** Count of distinct started analytics sessions with at least one server `analysis_completed` in the study window.
- **Event:** Server `analysis_completed`.
- **Denominator:** For a future completion rate, distinct sessions with `start_selection`; always publish the numerator, denominator, exclusions, and sample size.
- **Interpretation:** The server reached an analysis terminal success for the session flow.
- **Limitation:** It does not prove that the participant saw or understood the result. Current Phase 2 replay integrity is not yet validated.

## Question Engagement

- **Definition:** Count of distinct started sessions with `merchant_question_viewed` or `merchant_question_copied`, reported separately and as an optional union count.
- **Event:** Client `merchant_question_viewed`; client `merchant_question_copied`.
- **Denominator:** For a future engagement rate, distinct sessions with `analysis_completed` that were actually shown at least one question; observation notes must confirm eligibility.
- **Interpretation:** Viewed means exposure; copied means a stronger interaction. Neither proves the participant asked a merchant.
- **Limitation:** Render instrumentation can over- or under-count views, and copy-all is not equivalent to copying one high-value question.

## Merchant Return

- **Definition:** Count of distinct started sessions with the first server `merchant_reply_submitted` for the active flow.
- **Event:** Server `merchant_reply_submitted`.
- **Denominator:** For a future return rate, distinct question-eligible sessions with `merchant_question_viewed` or `merchant_question_copied`.
- **Interpretation:** A merchant reply entered the business workflow; analytics contains no raw reply text.
- **Limitation:** In a moderated Beta the reply may be simulated. Phase 2 replay can currently duplicate raw event records, so first-seen event-ID deduplication is required for analysis.

## Rejudge Completion

- **Definition:** Count of distinct started sessions with a server `rejudge_completed` for the active flow.
- **Event:** Server `rejudge_completed`.
- **Denominator:** For a future completion rate, distinct sessions with a valid `merchant_reply_submitted` that initiated rejudge.
- **Interpretation:** The server persisted a completed rejudgement outcome.
- **Limitation:** Three database-backed eval cases are BLOCKED, so current local evidence does not prove the full persisted Decision V1 → reply → V2/Delta chain.

## Selection Completion

- **Definition:** Count of distinct started sessions with client `candidate_selected` after a result was presented.
- **Event:** Client `candidate_selected`.
- **Denominator:** For a future completion rate, distinct sessions with `start_selection`; assisted and unassisted study tasks must be reported separately.
- **Interpretation:** A participant made an in-product final candidate choice.
- **Limitation:** It is not purchase, satisfaction, trust, or decision quality. Browser end-to-end validation is currently BLOCKED.

## Reporting rules

Any later rate must state numerator, denominator, unit of analysis, time window, exclusions, and sample size beside the result. Do not label fixed-eval pass counts as model accuracy, raw activity as conversion, or small-Beta observations as statistical significance.
