# AI Evaluation Matrix

Run date: 2026-08-13  
Runtime: deterministic fake/pure tests; no real Provider calls.  
Full result used below: backend 202 passed / 70 skipped; frontend 38 passed. DB-dependent cases skipped because `TEST_DATABASE_URL` was not configured.

| CASE ID | Category | Scenario | Input | Expected | Actual | Result | Failure Type |
|---|---|---|---|---|---|---|---|
| EXT-01 | Extraction | Complete fixed candidate | `candidate_a_complete_qingxiang.json` | Required explicit fields retain fixture semantics | `test_three_prd_fixed_candidates_preserve_required_semantics` passed | PASS | — |
| EXT-02 | Extraction | Unknown roast | `boundaries/unknown_roast.json` | Roast remains unknown | `test_extraction_boundaries_keep_unknown_conflict_and_unit_price_guardrails` passed | PASS | — |
| EXT-03 | Extraction | Missing price/weight | boundary fixtures | Missing values remain unknown; no invented unit price | Same boundary test passed | PASS | — |
| EXT-04 | Extraction | Conflicting fields | `boundaries/conflicting_fields.json` | Conflict is retained and does not improve certainty | Fixture boundary and conflict decision tests passed | PASS | — |
| EVD-01 | Evidence Safety | Product explicit fact | explicit product aroma | Appears in `known_facts` | Mixed-source answer test passed | PASS | — |
| EVD-02 | Evidence Safety | Product inferred fact | inferred roast | Does not enter “商品页能确认” | Mixed-source answer test passed | PASS | — |
| EVD-03 | Evidence Safety | Merchant explicit fact | merchant sample=true | Appears only in `merchant_facts` | Mixed-source answer test passed | PASS | — |
| EVD-04 | Evidence Safety | Marketing-heavy page | 兰花香/大师/高山 claims | Does not become verified taste or higher sufficiency | marketing safety tests passed | PASS | — |
| SEN-01 | Sensory | Qingxiang + light roast | explicit qingxiang/light | Bounded fresh and lower-fire interpretation | `test_qingxiang_and_light_roast_have_bounded_interpretations` passed | PASS | — |
| SEN-02 | Sensory | Heavy roast | explicit heavy | Bounded熟香/焙火 interpretation, no quality judgment | `test_heavy_roast_is_not_a_quality_judgement` passed | PASS | — |
| SEN-03 | Sensory | Unknown style | unknown qingxiang | No sensory claim | `test_marketing_or_unknown_never_becomes_verified_taste` passed | PASS | — |
| NEED-01 | Current Need | 清爽/低火味 vs heavy/light | two same-bucket candidates | Light ranks above heavy | low-fire regression passed | PASS | — |
| NEED-02 | Current Need | 熟香/焙火明显 | nongxiang/heavy vs qingxiang/light | Rich/heavy ranks above fresh/light | rich-need regression passed | PASS | — |
| NEED-03 | Current Need | No sensory Need | qingxiang vs nongxiang | No forced sensory tie-break | missing-Need regression passed | PASS | — |
| NEED-04 | Current Need | Budget range | `150–300`, `150-300`, `300以内` | 250 fits; 350 does not | parametrized budget test passed | PASS | — |
| QST-01 | Question | Counterfactual value | precomputed answer branches | Impact derives without side effects | `test_counterfactual_branch_is_side_effect_free_and_assigns_impact_levels` passed | PASS | — |
| QST-02 | Question | Empty high-value question set | completed generation, zero rows | Current Decision unlocks; snapshot recovers terminal state | DB-backed behavior test skipped; frontend recovery contract passed | NOT_AUTOMATED | QUESTION_LOW_VALUE |
| MRP-01 | MerchantReply | Negative sample answers | 不提供/没有/不可以 | normalized false | negation matrix passed | PASS | — |
| MRP-02 | MerchantReply | Positive sample answers | 可以/提供/有 | normalized true | positive matrix passed | PASS | — |
| MRP-03 | MerchantReply | Unknown vs explicit opposite product evidence | product unknown/same/opposite | unknown no conflict; opposite conflicts | conflict-boundary test passed | PASS | — |
| REJ-01 | Rejudge | Unrelated reply | evasive return-policy reply | V1 bounded preference/ranking retained | repository-stub rejudge test passed | PASS | — |
| REJ-02 | Rejudge | Aggregate saved replies | multiple replies across candidates | one immutable V2 and Delta | DB-backed test skipped | NOT_AUTOMATED | REJUDGE_INCONSISTENT |
| STATE-01 | State / Recovery | Need changes after Result/Rejudge | old Decision/questions/replies/Delta | all derived artifacts clear; extraction stays | pure invalidation + wiring tests passed | PASS | — |
| STATE-02 | State / Recovery | F5 during processing | snapshot current job=processing | resume Analysis | recovery helper/wiring tests passed | PASS | — |
| STATE-03 | State / Recovery | F5 after V2 Delta | snapshot has current Decision + Delta | resume Rejudge and keep Delta | recovery helper/wiring tests passed | PASS | — |
| STATE-04 | State / Recovery | Normal reopen/new tab | cached old identifiers, navigation not reload | Home | onboarding routing test passed | PASS | — |
| STATE-05 | State / Recovery | Merchant textarea draft reload | unsubmitted text | draft recovered | No persistence is implemented | NOT_AUTOMATED | STATE_RECOVERY_ERROR |

## Totals

- Total cases: 27
- PASS: 24
- FAIL: 0
- NOT_AUTOMATED: 3

The three `NOT_AUTOMATED` cases are excluded from the PASS count. Two require an isolated PostgreSQL test database; the textarea draft is a recorded P2 and was intentionally not implemented.
