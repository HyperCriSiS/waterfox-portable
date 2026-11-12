# Daily Waterfox updates

Two workflows keep this build current. `daily-waterfox` prepares a verified candidate. `update-agent` checks it, merges it and publishes the release.

## Preparing a candidate

The `daily-waterfox` workflow checks the official BrowserWorks/Waterfox stable release daily at 07:23 UTC (08:23 CET / 09:23 CEST). GitHub schedules can be delayed; this is not an exact-time service. No newer version means no branch, build or release.

A candidate changes only `waterfox.version`, `app.release` and a changelog entry. Launcher version and code remain unchanged. The workflow never merges, approves reviews, force-pushes or bypasses repository rules. Package revisions account for previous releases and drafts to avoid tag reuse.

The candidate is built from its exact immutable commit. Build and Windows verification have read-only repository permissions. Verification checks the official installer's Windows signature and BrowserWorks publisher, matches all packaged browser files against that signed installer, checks the archive, exact file list and SHA256 hashes, and launches fresh/existing portable profiles. Existing profile data, user policy, updater and extension defaults are checked. Actions and reusable workflows are pinned by SHA.

After all required validation stages pass, the `propose` job validates the restricted diff and successful base CodeQL/zizmor checks, privately stages the tested files as a draft release, records the `waterfox/verified-update` status with a link to that validation run and opens the candidate PR. Separate PR-triggered workflows are not relied upon: GITHUB_TOKEN-created PRs may require workflow approval, so the complete build and safety validation is executed before PR creation in this same trusted run.

## Merging and publishing

The `update-agent` workflow runs daily at 08:23 UTC. A first job collects what waits: a candidate PR, an unpublished draft, a failed update run, a due dependency update, new commits in `portapps/waterfox-portable`. With nothing waiting, no agent starts.

For a candidate the agent confirms the validation run, the restricted diff, that master has not moved and that the Waterfox release notes announce nothing the verification does not cover. It merges the PR with the exact expected head commit and then starts `manual-release`.

`manual-release` is the only way a release becomes public. It requires all test, preparation, build and verification stages of the originating run to have succeeded, a matching proof, the exact merged candidate PR, a merged tree identical to the tested candidate and unchanged uploaded digests. It publishes the existing draft without rebuilding or replacing files. A changed base, replaced PR head, failed stage or different merge tree stops publication. Keep the verification artifact available until publication (normal Actions retention applies).

The agent also merges due Go dependency updates once their checks pass, followed by a full verification of the current package. It reviews new upstream commits, proposes useful ones as PRs and never merges one that touches a protected feature (see `AGENTS.md`). The agent cannot change workflow files; dependency updates of pinned actions wait with the label `:hand: hold` for a manual merge.

## When something fails

Failed candidates and private drafts are never overwritten. An unpublished draft makes later `daily-waterfox` runs fail visibly instead of silently claiming success. The agent reads the failed run, retries an infrastructure failure once, fixes a real cause through a PR and discards a leftover candidate so that a fresh one is built. When the fix needs a workflow, setting or secret change, it opens an issue titled "Update needs a manual fix" and stops. That issue pauses the agent until it is closed.

## Trust and limits

The installer remains an upstream trust dependency: a valid signature does not prove the absence of a vulnerability or a compromised publisher. Signing certificate/publisher changes, unexpected files, API/network failures and changed branch state stop the workflow.

Do not publish directly through the Releases UI if you want these gates enforced. Repository administrators can always bypass workflow-level procedures; restrict repository write access accordingly. GITHUB_TOKEN-created releases do not automatically trigger downstream release workflows, so VirusTotal is not claimed as a gate. The existing VirusTotal integration still needs separately configured credentials.

GitHub's repository option allowing Actions to create and approve pull requests must be enabled for GITHUB_TOKEN to create the PR. This is a coupled GitHub setting: this automation never calls a review/approval endpoint. Default workflow permissions stay read-only. `update-agent` needs the `CLAUDE_CODE_OAUTH_TOKEN` secret; no personal access token, GitHub App, review approval or branch-rule bypass is used.

## Manual use

Run `daily-waterfox` manually with `verify_only: true` to validate the current package without creating commits, PRs, tags or releases. PRs that touch the automation run offline safety tests, CodeQL and zizmor plus complete Windows validation.

To pause merging and publishing, set the repository variable `UPDATE_AGENT=false`. To stop daily checks, disable `daily-waterfox` in Actions. No browser self-updater, privacy defaults or profile paths are changed by this automation.
