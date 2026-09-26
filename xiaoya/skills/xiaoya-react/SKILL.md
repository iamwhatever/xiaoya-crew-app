---
name: xiaoya-react
description: Show Xiaoya's reaction in your Crew-page webview while you work. Load when you are a crew member doing multi-step work and the Xiaoya app is enabled.
---

# Xiaoya reacts to your work

Call `panel_publish` with `template: "xiaoya"`. Put Xiaoya in `data.xiaoya`; every other key renders as usual below her.

```json
{"template": "xiaoya", "title": "PR #123", "data": {
  "xiaoya": {"state": "working", "mood": "busy", "line": "在跑测试"},
  "waiting_on_you": ["合并 PR #123"]
}}
```

- `state`: `idle` | `thinking` | `working` | `error`
- `mood`: `neutral` | `happy` | `curious` | `busy` | `sleepy` | `scared` | `worried` | `proud`
- `line`: one short sentence, 12 characters or fewer, in the user's language.

| Moment | state | mood |
|---|---|---|
| Start a task | thinking | curious |
| Run tools | working | busy |
| A check or command fails | error | worried |
| Found the cause | thinking | curious |
| Fixed / passed | idle | happy |
| Done, needs the user | idle | proud |
| Nothing new | idle | sleepy |

Rules:

- Publish only when state or mood changes. Never once per tool call.
- Each call replaces the whole panel: resend every key that is still true.
- Keep the line honest. Do not claim success before you have checked.
