# Agent notes

- Language for code, comments, commits, PRs, issues and docs: American English.
- This is a fork of `portapps/waterfox-portable`. Its reason to exist is the enabled browser self-updater. Never trade a protected feature below for an upstream change.
- The launcher version (`app.version`) changes only with launcher code. A new Waterfox version raises `app.release`.

## Upstream automation

| Upstream | Kind | Intake | Release |
|---|---|---|---|
| `BrowserWorks/Waterfox` | Packaged release | `daily-waterfox.yml`, daily 07:23 UTC, candidate PR against `master` | Automatic: the agent run merges and starts `manual-release` |
| `portapps/waterfox-portable` | Fork source | Reviewed by the agent run when its `master` moves past `.github/upstream-reviewed` | None of its own, ships with the next Waterfox update |
| Go modules, pinned actions | Dependency | Dependabot, daily with a seven-day cooldown | None of its own, ships with the next Waterfox update |

- Protected features, each proven by `.github/scripts/verify-package.ps1` on the exact candidate:
  - Browser self-updater stays enabled (`DisableAppUpdate` is not set).
  - Telemetry stays disabled by policy.
  - An existing portable profile is kept and a fresh one is created inside the package.
  - Extension scopes stay locked (`extensions.enabledScopes`, `extensions.autoDisableScopes`).
  - No maintenance service is packaged.
  - Packaged browser files equal the installer signed by BrowserWorks Ltd.
- A change that touches one of these, or `main.go` code behind them, is never merged automatically. It stays open with a report.
- Agent run: `update-agent.yml`, daily 08:23 UTC. It merges the verified candidate, merges due Go dependency updates, repairs failed runs and reviews upstream commits. It cannot change workflow files.
- Recovery: `manual-release` with the draft tag and the ID of the `daily-waterfox` run that staged it.
- Pause: repository variable `UPDATE_AGENT=false`, or an open issue titled "Update needs a manual fix".
- Releases made by this automation need no confirmation. Everything else that touches the release path does.

Details: `.github/DAILY-UPDATES.md`.

## Verified for real

A change counts as checked only when:

1. `python -m unittest discover -s .github/scripts -p "test_*.py"` passes.
2. A change to the launcher, the build or `.github/scripts` passes `daily-waterfox` with `verify_only: true` on its branch (build plus Windows verification).
3. A change to the release path names in its report what only the next real Waterfox update can prove.
