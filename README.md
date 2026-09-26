# Xiaoya for Kiro Crew

A Kiro Crew app that puts a small companion, Xiaoya, in each crew's webview on the Crew page. While a crew works, she shows what it is doing and how it feels about it.

![Xiaoya in a crew's drawer during a PR check](docs/demo.gif)

No change to Kiro Crew core. The app uses two things Kiro Crew already has:

| Part | What it does | Built on |
|---|---|---|
| `xiaoya/hooks.py` | Installs `xiaoya.html` into the operator template dir on enable and keeps it there | App Kit `on_startup` / `on_shutdown` hooks |
| `xiaoya/templates/xiaoya.html` | The character plus the generic data view | Crew Webview templates |
| `xiaoya/skills/xiaoya-react` | Tells a crew when to publish and what to send | App skills |

The hook never overwrites or deletes an `xiaoya.html` it did not write (ownership marker on line 1).

## Install

```bash
kirocrew app install ./xiaoya
kirocrew config set agent.apps_trusted '["xiaoya"]'
kirocrew app enable xiaoya
```

Trusting the app lets its Python hooks run inside the gateway process. Order matters: install first, then trust. A grant set before a local install is refused ("execution trust predates repository binding"). If you must set it first, also add the name to `agent.apps_trusted_local`.

### Who sees the skill

The `xiaoya-react` skill reaches the default `kirocrew` agent. A custom agent template (for example a crew member's) does not see it unless its agent JSON maps it in `resources`:

```json
"resources": ["skill://~/.kiro/crew/skills/xiaoya-react/SKILL.md"]
```

Without that entry, the crew can still publish with `template: "xiaoya"`; it just is not told to. Details: [docs/verification.md](docs/verification.md).

Undo: `kirocrew app disable xiaoya` then `kirocrew app uninstall xiaoya`. The template file stays in `~/.kiro/crew/panel-templates/xiaoya.html`, so panels a crew already published with it keep rendering; they just stop changing, because the crew no longer has the skill. The file is inert markup. To delete it too, check its first line is `<!-- installed-by-app: xiaoya -->`, then `rm ~/.kiro/crew/panel-templates/xiaoya.html`; after that, those old panels show a render error until the crew publishes again.

## Publishing

A crew calls `panel_publish`:

```json
{"template": "xiaoya", "title": "PR #123", "data": {
  "xiaoya": {"state": "working", "mood": "busy", "line": "在跑测试"},
  "waiting_on_you": ["合并 PR #123"]
}}
```

- `state`: `idle` · `thinking` · `working` · `error`
- `mood`: `neutral` · `happy` · `curious` · `busy` · `sleepy` · `scared` · `worried` · `proud`
- `line`: one short sentence. Rendered with `textContent`, never as markup.

![All moods, dark and light](docs/gallery.png)

## Development

The template is rebuilt from Kiro Crew's own `default.html`, so you need a Kiro Crew checkout:

```bash
python3 dev/build.py /path/to/KiroCrew/src     # rewrite xiaoya/templates/xiaoya.html
python3 dev/gallery.py /path/to/KiroCrew/src   # dev/out/gallery.html, every mood
python3 dev/demo.py /path/to/KiroCrew/src      # dev/out/demo/step-*.html, a scripted run
```

Run the tests (the compose tests need `kiro_crew` importable and skip without it):

```bash
python -m pytest tests -q
```

Edit the character in `dev/stage.fragment.html` (SVG + CSS) and `dev/stage.script.html` (mood logic).

The panel CSP allows only `data:` / `blob:` images and no media, so the character is inline SVG. Motion stops under reduced-motion and has a pause button.

Design notes: [docs/design.md](docs/design.md).

## Notes

- The character is an original placeholder, not the "赛博小雅" from the Bilibili videos. That design belongs to its author.
- `xiaoya/templates/xiaoya.html` contains Kiro Crew's `default.html` template, used under the Apache License 2.0 ([kirodotdev/KiroCrew](https://github.com/kirodotdev/KiroCrew)). This repo is Apache-2.0 too: see [LICENSE](LICENSE) and [NOTICE](NOTICE).
