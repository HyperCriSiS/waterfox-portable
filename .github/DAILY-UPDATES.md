# Daily Waterfox candidates

The `daily-waterfox` workflow checks the official BrowserWorks/Waterfox stable release daily at 07:23 UTC (08:23 CET / 09:23 CEST). GitHub schedules can be delayed; this is not an exact-time service. No newer version means no branch, build or release.

The introductory mode creates **draft releases only**. It never merges, approves reviews or publishes automatically. A successful new candidate produces a branch changing only `waterfox.version`, `app.release` and a changelog entry, with a comparison/PR creation link in the draft notes. Launcher version and code remain unchanged. Draft release revisions account for previous drafts to avoid tag reuse.

The candidate is built from its exact immutable commit. Build and Windows verification have read-only repository permissions. Verification checks the official installer's Windows signature and BrowserWorks publisher, matches all packaged browser files against that signed installer, checks the archive, exact file list and SHA256 hashes, and launches fresh/existing portable profiles. Existing profile data, user policy, updater and extension defaults are checked. Publishing permissions exist only in the separate draft/publish jobs. Actions and reusable workflows are pinned by SHA.

The installer remains an upstream trust dependency: a valid signature does not prove the absence of a vulnerability or a compromised publisher. Signing certificate/publisher changes, unexpected files, API/network failures and changed branch state stop the workflow. Failed candidate branches are retained for inspection and never force-pushed. After resolving a failure, remove the failed candidate branch before retrying; do not remove a successful candidate's branch before merging its PR.

## Initial validation

Run `daily-waterfox` manually with `verify_only: true`. This validates the current package without creating commits, PRs, tags or releases. PRs run offline safety tests, CodeQL and zizmor; the complete Windows validation must also pass before activation. Keep draft mode until an actual new upstream version has completed the candidate path successfully and been reviewed.

No personal access token, GitHub App or permission for Actions to approve reviews is required: the build is explicitly called by the same workflow. The human reviewer opens the PR through the comparison link. Ordinary PR checks run separately and do not replace the explicit build and verification gates.

## Review and publish

Open the candidate PR from the comparison link in the draft notes, review and merge it, then run `manual-release` on master with the draft tag and the originating successful `daily-waterfox` run ID. It accepts only a successful trusted master run, matching proof, an exact merged candidate PR and unchanged uploaded asset digests. It publishes that draft without rebuilding or replacing assets. Keep the verification artifact available until publication (normal Actions retention applies).

Do not publish directly through the Releases UI if you want these gates enforced. Repository administrators can always bypass workflow-level procedures; restrict repository write access accordingly. GITHUB_TOKEN-created releases do not automatically trigger downstream release workflows, so VirusTotal is not claimed as a gate. The existing VirusTotal integration still needs separately configured credentials.

To stop daily checks, disable `daily-waterfox` in Actions. Manual validation remains available when the workflow is enabled. No browser self-updater, privacy defaults or profile paths are changed by this automation.
