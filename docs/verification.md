# Xiaoya verification (items 2 and 3)

Checked against `/workspace/KiroCrew` at `47594b8390`. All runs used a throwaway `KIROCREW_HOME` under `/tmp/xiaoya-verify-*`; the live `~/.kiro/crew` config and apps were not touched. Harness: `~/.kiro/crew/xiaoya-verify-work/run_verify.py` (install -> register_app -> enable_app -> init_hooks_system -> on_app_enable -> on_app_disable -> SkillsLoader).

## Q1: are `backend.hooks.on_startup` / `on_shutdown` called for a third-party app with no `entryPoint`?

Verdict: YES. The manifest and `hooks.py` are correct as written; nothing changed. A per-app `agent.apps_trusted` grant is enough at runtime; `apps_allow_third_party` is not needed. One install-order catch: see "Grant vs local install" below.

Code path (enable):

- `apps/manager.py:1899` `enable_app` -> `:1931` `app_execution_denied(action="enable")`.
- Dashboard / gateway-routed CLI enable: `apps/routes.py:2016` -> `apps/hooks_integration.py:351` `on_app_enable`.
- `hooks_integration.py:363` `app_execution_denied(action="hook_enable_register")` -> `apps/execution.py:623` `_execution_admission`: `:646` name in `apps_trusted` -> `:661` admitted (`builtin or granted or third_party_execution_allowed()`).
- `hooks_integration.py:396` reads `manifest.backend.hooks`; nothing on this path checks `entryPoint`. `entryPoint` only gates spawning a backend PROCESS (`apps/backend.py:5307`), which Xiaoya does not need.
- `hooks_integration.py:446-449` -> `apps/lifecycle.py:405` `_invoke` -> `:478` `_resolve_hook` -> `:385` `load_app_module(app, app_dir(app), "hooks:on_startup")` -> `:481` `func(ctx)`.
- Gateway boot runs the same steps: `hooks_integration.py:740` `on_gateway_startup` -> `:758` admission -> `:828` `_invoke`. Disable / stop: `on_app_disable` (`:640`) and `on_gateway_shutdown` (`:896`) -> `lifecycle.py:476` resolves the already-loaded `on_shutdown` first.

Hook spec format: `"hooks:on_startup"` matches `HooksConfig._HOOK_PATH_RE` (`apps/manifest.py:673`, `module.path:callable`). It resolves to `<app_dir>/hooks.py` (`apps/module_loader.py:248-249`).

Import semantics: file-path load via `spec_from_file_location` (`module_loader.py:290`). `sys.path` is NOT changed, so `import hooks` from a sibling would not resolve; Xiaoya does not need it. `__file__` is the installed `hooks.py`, so `_SOURCE` finds `templates/xiaoya.html`. `from kiro_crew.agent_panel ...` and `kiro_crew.atomic_write` import fine (gateway process). Third-party loads pass the same admission check again (`module_loader.py:274-285`).

`ctx`: an `AppContext` (`apps/context.py:71` `health: AppHealthStatus`); `mark_degraded(issue)` exists at `context.py:33`. A degraded health is published and reported (`hooks_integration.py:239`).

Real run (trusted):

| step | result |
|---|---|
| install_app | ok, v0.1.0 |
| enable_app | ok |
| on_app_enable | `{'hooks_startup': 'ok'}`, health healthy |
| template | `<home>/panel-templates/xiaoya.html`, first line = MARKER |
| on_app_disable | `{'hooks_shutdown': 'ok'}`; file kept (matches the parallel worker's new keep-on-shutdown `on_shutdown`) |

Real run (no grant): `enable_app` refused "blocked by execution policy"; `on_app_enable` skipped hooks; no template written.

Grant vs local install (`kirocrew app install <dir>`): with `apps_trusted: ["xiaoya"]` set BEFORE install, install is refused: "execution trust predates repository binding and is inactive for repository-backed code". Cause: `manager.py:714` `repository_bound_grant_denied` -> `execution.py:502-512`: a name-only grant with no installed record is treated as repository-backed unless the name is also in `agent.apps_trusted_local`. Both of these worked in real runs:

- `apps_trusted: ["xiaoya"]` + `apps_trusted_local: ["xiaoya"]`, then install; or
- install first with no grant, then add `apps_trusted: ["xiaoya"]` (runtime check finds a locally-installed record and admits).

README install steps should say one of these.

## Q2: does the `skills` entry reach crew members?

Verdict: PARTLY. The skill registers and parses correctly (no SKILL.md change needed). It reaches the default `kirocrew` agent and any agent that maps it via `skill://`. It does NOT reach an unmapped custom template, which includes the crew-member templates here (`kirocrew-worker`, `kirocrew-conductor`, ...).

Registration: `apps/bridges.py:3210` `register_app` (called from CLI install/enable, `cli_commands.py:1161/1194`, and boot `backend.py:5277`) -> `:3286` `_register_skills` (`:1146`) symlinks `skills/xiaoya/xiaoya-react` and flat `skills/xiaoya-react` into `<home>/skills/`. Refused without an execution grant (`bridges.py:3242`).

Frontmatter: parsed by `SkillsLoader` (`skills.py`, `parse_frontmatter`). Real run: `list_skills()` returns key `xiaoya/xiaoya-react`, name `xiaoya-react`, the full description, `inject_on_trigger: true`. After `disable_app` it is gone (`skills.py:762` `_disabled_app_names`).

Who sees it:

| agent | startup catalog / trigger | skill_search |
|---|---|---|
| `kirocrew` (default) | yes | yes |
| custom, maps `skill://` incl. it | yes (scoped) | yes |
| custom, no `skill://` (crew members) | no | no |

- Catalog gate: `context.py:3032-3048` `_skills_injection_plan` -> inject only if mapped or agent == `kirocrew`; trigger injection also skipped for custom agents (`context.py:5573`).
- `skill_search`: `mcp_tools/skills.py:167` -> `dashboard/handlers/prompts.py` `api_skills` -> `agent_discovery.py:1350-1359` `session_skill_globs` returns `[]` for an unmapped non-kirocrew template -> `skills.py:7288` `if only == []: return []`.
- Live proof: `skill_search(action="list")` from this `kirocrew-worker` session returns "End of this agent's available skill list."

Consequence: the SKILL.md says "Load when you are a crew member", but members on custom templates cannot find it. Fixing that needs either a `skill://` resource in each member's agent JSON, or a core change; it is not fixable inside `xiaoya/`.

## Files changed

None. `xiaoya/app.json`, `xiaoya/hooks.py` and `xiaoya/skills/xiaoya-react/SKILL.md` are left as found (the `hooks.py` diff in the tree is the other worker's `on_shutdown` change). Temp homes `/tmp/xiaoya-verify-*` were left in place (a safety policy blocked `rm -rf`); they hold only test data.
