# Agent notes

- Language for code, comments, commits, PRs, issues and docs: American English.
- This is a fork of `portapps/waterfox-portable`. Its reason to exist is the enabled browser self-updater. Never trade a protected feature below for an upstream change.
- The launcher version (`app.version`) changes only with launcher code. A new Waterfox version raises `app.release`.

## Upstream automation

| Upstream | Kind | Intake | Release |
|---|---|---|---|
| `BrowserWorks/Waterfox` | Packaged release | `daily-waterfox.yml`, daily 07:23 UTC, candidate PR against `master` | Automatic: the agent run starts `manual-release`, which merges and publishes |
| `portapps/waterfox-portable` | Fork source | Reviewed by the agent run when its `master` moves past `.github/upstream-reviewed`; proposals wait for a person | None of its own, ships with the next Waterfox update |
| Go modules, pinned actions | Dependency | Dependabot, daily with a seven-day cooldown | None of its own, ships with the next Waterfox update |

- Protected features and what `.github/scripts/verify-package.ps1` proves about each on the exact candidate:
  - Browser self-updater: `updater.exe` is packaged and the packaged policies do not set `DisableAppUpdate`.
  - User policies: a policy from `data/policies.json` arrives in the packaged policies.
  - Portable profile: a fresh start creates it inside the package, a second start keeps an existing one.
  - Extension scopes: `extensions.enabledScopes` and `extensions.autoDisableScopes` stay locked.
  - No maintenance service is packaged.
  - Every packaged browser file comes unchanged from the installer signed by BrowserWorks Ltd.
- The verification starts the browser twice headless. It does not exercise an actual browser update or other launcher behavior. Launcher code (the Go files, `build.xml`, `res`) is therefore never merged by the automation; such a PR waits for a person with the label `:hand: hold`.
- Agent run: `update-agent.yml`, daily 08:23 UTC. It checks the candidate and starts `manual-release`, merges due Go dependency updates, repairs failed runs in `.github/scripts` and proposes upstream commits. It cannot change workflow files.
- Recovery: `manual-release` with the draft tag and the ID of the `daily-waterfox` run that staged it.
- Pause: repository variable `UPDATE_AGENT=false`, or an open issue titled "Update needs a manual fix" that the automation opened.
- Releases made by this automation need no confirmation. Everything else that touches the release path does.
- Exception to "nothing refers to an assistant": `update-agent.yml` names the action, the model and the secret it needs. Nothing else in the repository does.

Details: `.github/DAILY-UPDATES.md`.

## Verified for real

A change counts as checked only when:

1. `python -m unittest discover -s .github/scripts -p "test_*.py"` passes.
2. A change to the launcher, the build or `.github/scripts` passes `daily-waterfox` with `verify_only: true` on its branch (build plus Windows verification).
3. A change to the release path names in its report what only the next real Waterfox update can prove.
