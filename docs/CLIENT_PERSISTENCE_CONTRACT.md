# Client Persistence Contract

Status: current and binding for Phase 15.

## Long-lived browser stores

`guancha.selection-bridge.v1` uses schema version 3 and is serialized from a
field-level allowlist. It is a recovery anchor, not a presentation cache.

Allowed selection data:

- one selection-session UUID;
- at most five candidate anchors containing only local/server identity, A-E
  label, closed extraction status/error, and at most two image anchors;
- current Decision, Question, and Rejudge UUIDs plus closed status values;
- a UUID-to-UUID MerchantReply map and Reply anchors containing only UUIDs,
  closed processing/parse states, and ISO timestamps.

The following never enter the selection bridge: Need or other user free text,
merchant reply text/summary, extracted fields, decision/reasons/risk/evidence,
questions, answer presentation, Decision Delta presentation, preview/data URI,
File/Blob metadata, job maps, raw AI input/output, secrets, cookies, API keys,
or database URLs. Unknown fields and invalid structures are discarded.

On every load, old selection data is sanitized to schema v3 and the cleaned
value replaces the backing value. Corrupt data is removed. The legacy
`guancha-prototype-v2` object is migrated only through the same allowlists and
then removed; privacy takes priority over recovering unsafe presentation data.

Server state is authoritative. After reload, Need, current Decision, questions,
answer, and Decision Delta are fetched from the selection-session snapshot and
related server endpoints. A Need typed but not submitted to a server session may
be lost on refresh by design.

`guancha.ui-session.v1` stores only closed navigation/onboarding state and the
stable active-candidate identity. Preference controls are stored only as bounded
closed selections. `guancha.preference-evidence.v1` remains a bounded, explicit
low-confidence evidence store. Neither accepts MerchantReply content.

`guancha.local-post-purchase.v1` is a separate, explicit user-content contract
for the local tea warehouse and brewing journal. It must not receive MerchantReply
or selection presentation objects.

IndexedDB `guancha.pending-images.v1` is a temporary upload-resume cache. It is
not long-lived profile state. Browser/session TTL and eviction policy remain a
documented P2 boundary; Phase 15 does not change its schema.

