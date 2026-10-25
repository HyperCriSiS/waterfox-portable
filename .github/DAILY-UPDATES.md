# Daily Waterfox candidates

The `daily-waterfox` workflow checks the official BrowserWorks/Waterfox stable release daily at 07:23 UTC (08:23 CET / 09:23 CEST). GitHub schedules can be delayed; this is not an exact-time service. No newer version means no branch, build or release.

The workflow automatically creates and merges **only its own verified Waterfox update PR**, then publishes the exact tested files. A candidate changes only `waterfox.version`, `app.release` and a changelog entry. Launcher version and code remain unchanged. It never merges unrelated PRs, approves reviews, force-pushes or bypasses repository rules. Package revisions account for previous releases and drafts to avoid tag reuse.

The candidate is built from its exact immutable commit. Build and Windows verification have read-only repository permissions. Verification checks the official installer's Windows signature and BrowserWorks publisher, matches all packaged browser files against that signed installer, checks the archive, exact file list and SHA256 hashes, and launches fresh/existing portable profiles. Existing profile data, user policy, updater and extension defaults are checked. Publishing/merge permissions exist only in the separate release job. Actions and reusable workflows are pinned by SHA.

After all required validation stages pass, the release job validates the restricted diff and successful base CodeQL/zizmor checks, privately stages the tested files, records the `waterfox/verified-update` status with a link to that validation run, creates the PR and merges it using the exact expected candidate SHA. It checks that the merge commit contains the candidate and has the identical tested tree. Only then are release asset digests checked again and the release published. A changed base, replaced PR head, failed stage or different merge tree stops publication. Separate PR-triggered workflows are not relied upon: GITHUB_TOKEN-created PRs may require workflow approval, so the complete build and safety validation is explicitly executed before PR creation in this same trusted run.

The installer remains an upstream trust dependency: a valid signature does not prove the absence of a vulnerability or a compromised publisher. Signing certificate/publisher changes, unexpected files, API/network failures and changed branch state stop the workflow. Failed candidates and private drafts are retained for inspection and never overwritten. An unresolved draft makes later checks fail visibly instead of silently claiming success. Inspect and resolve the failed run before retrying; a successfully merged candidate with a failed final publication can use the recovery workflow below.

## Initial validation

Run `daily-waterfox` manually with `verify_only: true`. This validates the current package without creating commits, PRs, tags or releases. PRs run offline safety tests, CodeQL and zizmor plus complete Windows validation before activation. Normal scheduled runs and manual runs with `verify_only: false` perform the automatic merge and release when a newer stable version exists.

GitHub's repository option allowing Actions to create and approve pull requests must be enabled for GITHUB_TOKEN to create the PR. This is a coupled GitHub setting: this automation never calls a review/approval endpoint. Default workflow permissions stay read-only; only the release job receives PR write access. No personal access token, GitHub App, review approval or branch-rule bypass is used. If future repository rules require human reviews or additional candidate checks, automatic merging will stop until those rules are satisfied.

## Recovery

After inspecting a failed final publication, run `manual-release` on master with the private draft tag and the originating `daily-waterfox` run ID. It requires all test, preparation, build and verification stages to have succeeded, a matching proof, the exact merged candidate PR and unchanged uploaded digests. The originating run may have failed only after those required stages. It publishes the existing draft without rebuilding or replacing files. Keep the verification artifact available until publication (normal Actions retention applies).

Do not publish directly through the Releases UI if you want these gates enforced. Repository administrators can always bypass workflow-level procedures; restrict repository write access accordingly. GITHUB_TOKEN-created releases do not automatically trigger downstream release workflows, so VirusTotal is not claimed as a gate. The existing VirusTotal integration still needs separately configured credentials.

To stop daily checks, disable `daily-waterfox` in Actions. Manual validation remains available when the workflow is enabled. No browser self-updater, privacy defaults or profile paths are changed by this automation.
