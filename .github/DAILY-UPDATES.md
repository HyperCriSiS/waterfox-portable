# Daily Waterfox updates

Three workflows keep this build current. `daily-waterfox` prepares a verified candidate. `update-agent` checks it and starts `manual-release`, which merges it and publishes the release.

## Preparing a candidate

The `daily-waterfox` workflow checks the official BrowserWorks/Waterfox stable release daily at 07:23 UTC (08:23 CET / 09:23 CEST). GitHub schedules can be delayed; this is not an exact-time service. No newer version means no branch, build or release.

A candidate changes only `waterfox.version`, `app.release` and a changelog entry. Launcher version and code remain unchanged. The workflow never merges, approves reviews, force-pushes or bypasses repository rules. Package revisions account for previous releases and drafts to avoid tag reuse.

The candidate is built from its exact immutable commit. Build and Windows verification have read-only repository permissions. Verification checks the official installer's Windows signature and BrowserWorks publisher, requires every packaged browser file to come unchanged from that signed installer, checks the archive, exact file list and SHA256 hashes, and launches fresh/existing portable profiles. Existing profile data, user policy, updater and extension defaults are checked. Actions and reusable workflows are pinned by SHA.

While the candidate builds, the workflow starts zizmor on master, because a merge made with the workflow token starts no push workflows. After all required validation stages pass, the `propose` job validates the restricted diff and successful base CodeQL/zizmor checks, privately stages the tested files as a draft release, records the `waterfox/verified-update` status with a link to that validation run and opens the candidate PR. Separate PR-triggered workflows are not relied upon: GITHUB_TOKEN-created PRs may require workflow approval, so the complete build and safety validation is executed before PR creation in this same trusted run.

## Merging and publishing

The `update-agent` workflow runs daily at 08:23 UTC. A first job collects what waits: a candidate PR, an unpublished draft, a failed update run, a due dependency update, new commits in `portapps/waterfox-portable`. With nothing waiting, or while a `daily-waterfox` run is still in progress, no agent starts.

For a candidate the agent confirms the restricted diff and that the Waterfox release notes announce nothing the verification does not cover. It then starts `manual-release` and never merges a candidate itself.

`manual-release` is the path this automation uses to make a release public. It requires all test, preparation, build and verification stages of the originating run to have succeeded, a matching proof, the verified draft with unchanged uploaded digests and a PR that identifies the exact candidate. Only then does it merge that PR with the exact expected head commit, and only while master is still the validated base. It checks that the merge commit contains the candidate and has the identical tested tree, and publishes the existing draft without rebuilding or replacing files. A changed base, replaced PR head, failed stage or different merge tree stops publication. Keep the verification artifact available until publication (normal Actions retention applies).

The agent also merges due Go dependency updates once their checks pass, followed by a full verification of the current package. It reviews new upstream commits and proposes useful ones as PRs; upstream and launcher code is never merged by the automation and waits for a person with the label `:hand: hold`. The agent cannot change workflow files, so dependency updates of pinned actions wait the same way.

## When something fails

Failed candidates and private drafts are never overwritten. An unpublished draft makes later `daily-waterfox` runs fail visibly instead of silently claiming success. The agent reads the failed run, fixes a real cause in `.github/scripts` through a PR and discards a leftover candidate so that a fresh one is built. When the fix needs launcher code or a workflow, setting or secret change, it opens an issue titled "Update needs a manual fix" and stops. That issue pauses the agent until it is closed. A failure of `update-agent` itself is reported only by GitHub's notification for failed scheduled workflows.

The agent job holds a token that can write to the repository, and it reads release notes, logs and upstream commits. Its limits (publish only through `manual-release`, never push to master) are instructions, not technical barriers. A ruleset that requires pull requests on master would turn the second one into a barrier.

## Trust and limits

The installer remains an upstream trust dependency: a valid signature does not prove the absence of a vulnerability or a compromised publisher. Signing certificate/publisher changes, unexpected files, API/network failures and changed branch state stop the workflow.

Do not publish directly through the Releases UI if you want these gates enforced. Repository administrators can always bypass workflow-level procedures; restrict repository write access accordingly. GITHUB_TOKEN-created releases do not automatically trigger downstream release workflows, so VirusTotal is not claimed as a gate. The existing VirusTotal integration still needs separately configured credentials.

GitHub's repository option allowing Actions to create and approve pull requests must be enabled for GITHUB_TOKEN to create the PR. This is a coupled GitHub setting: this automation never calls a review/approval endpoint. Default workflow permissions stay read-only. `update-agent` needs the `CLAUDE_CODE_OAUTH_TOKEN` secret; no personal access token, GitHub App, review approval or branch-rule bypass is used.

## Manual use

Run `daily-waterfox` manually with `verify_only: true` to validate the current package without creating commits, PRs, tags or releases. PRs that touch the automation run offline safety tests, CodeQL and zizmor plus complete Windows validation.

To pause merging and publishing, set the repository variable `UPDATE_AGENT=false`. To stop daily checks, disable `daily-waterfox` in Actions. No browser self-updater, privacy defaults or profile paths are changed by this automation.
