---
name: zai-model-availability
description: "How to check which z.ai GLM models a given API key/plan actually has access to, and the known FlashX gap on SwegOn's account"
metadata: 
  node_type: memory
  type: reference
  originSessionId: ff4e9b63-a33f-439d-88ba-7fe0971ae21c
  modified: 2026-07-22T16:08:30.961Z
---

z.ai exposes two OpenAI-compatible endpoints that both work with the same
key: `https://api.z.ai/api/coding/paas/v4` (Coding Plan) and
`https://api.z.ai/api/paas/v4` (standard pay-as-you-go). `GET
{base}/models` lists invokable model ids for the key, but it's not fully
authoritative — some gated variants (seen: `glm-4.7-flash`) answered chat
completions successfully despite not appearing in that list.

**Confirmed 2026-07-22** on SwegOn's `ZAI_API_KEY` (stored in
`/home/swegon/AI_Agent/Aio_df/.env`, line has a trailing `# comment` —
strip it with `sed 's/^ZAI_API_KEY=//' | awk '{print $1}'`, not a naive
`cut -d= -f2-`, or the comment text gets appended to the key and auth fails
with a confusing 401): `glm-4.5`, `glm-4.5-air`, `glm-4.6`, `glm-4.7`,
`glm-4.7-flash`, `glm-5`, `glm-5-turbo`, `glm-5.1`, `glm-5.2` all work.
`glm-4.7-flashx` returns `429 {"code":"1113","message":"Insufficient
balance or no resource package. Please recharge."}` on **both** endpoints —
this is a genuine account/plan gap on z.ai's side (FlashX apparently needs
a separate resource package from the Coding Plan subscription), not
something fixable from the Aio_df side. If asked to use FlashX again,
re-test with the same curl pattern before assuming it's fixed — z.ai may
have since enabled it, or SwegOn may have purchased the package.

**How to apply**: before wiring a new z.ai model into `config.yaml`, do a
quick live curl test (10-token max_tokens) against the coding-plan endpoint
first — cheaper than discovering a 429 after the user's already been told
it's live.
