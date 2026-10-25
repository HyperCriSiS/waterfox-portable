import copy
import base64
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
import waterfox_update as update

PROPS = 'app.version = 1.0.1\napp.release = 2\nwaterfox.version = 6.7.6\ncore.dir = ../portapps\n'
RELEASE = dict(tag_name='6.7.7', draft=False, prerelease=False, html_url='https://github.com/BrowserWorks/waterfox/releases/tag/6.7.7')


class UpdateTests(unittest.TestCase):
    def test_stable_source_and_version(self):
        self.assertEqual(update.stable_release(RELEASE), '6.7.7')
        for changes in [dict(draft=True), dict(prerelease=True), dict(html_url='https://example.com/6.7.7'), dict(tag_name='6.7.7\ncontents=write')]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                update.stable_release(dict(RELEASE, **changes))

    def test_versions_reject_untrusted_input(self):
        for value in ['', 'v6.7.7', '6.7.7-beta', '../6.7.7', '6.7.7;echo x', '6.7.7\n', '999999.0.0', None]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                update.version(value)
        self.assertGreater(update.version('6.10.0'), update.version('6.9.9'))
        self.assertEqual(update.version('6.7.7'), update.version('6.7.7.0'))

    def test_only_allowed_properties_change(self):
        self.assertEqual(update.update_properties(PROPS, '6.7.7', 3), PROPS.replace('app.release = 2', 'app.release = 3').replace('waterfox.version = 6.7.6', 'waterfox.version = 6.7.7'))

    def test_downgrades_duplicates_and_bad_revision_fail(self):
        for browser, revision in [('6.7.6', 3), ('6.7.5', 3), ('6.7.7', 2), ('6.7.7', 65536)]:
            with self.subTest(browser=browser, revision=revision), self.assertRaises(ValueError):
                update.update_properties(PROPS, browser, revision)
        with self.assertRaises(ValueError):
            update.update_properties(PROPS + 'waterfox.version = 6.7.6\n', '6.7.7', 3)

    def test_wrong_artifact_identity_or_manifest_fails(self):
        tag, browser, sha = '1.0.1-3', '6.7.7', 'a' * 40
        names = ['checksums.txt', f'WaterfoxSetup-{browser}.exe', f'waterfox-portable-win64-{tag}-setup.exe', f'waterfox-portable-win64-{tag}.7z', 'waterfox-portable-win64.exe']
        proof = dict(tag=tag, browser=browser, sha=sha, hashes={name: 'b' * 64 for name in names})
        update.validate_proof(proof, sha, tag, browser)
        for field in ['sha', 'tag', 'browser']:
            bad = copy.deepcopy(proof)
            bad[field] = 'unexpected'
            with self.assertRaises(ValueError):
                update.validate_proof(bad, sha, tag, browser)
        for name, digest in [('../evil.exe', 'b' * 64), ('checksums.txt', 'not-a-hash')]:
            bad = copy.deepcopy(proof)
            bad['hashes'][name] = digest
            with self.assertRaises(ValueError):
                update.validate_proof(bad, sha, tag, browser)

    def run_prepare(self, responses, verify=False):
        with tempfile.TemporaryDirectory() as folder:
            previous = Path.cwd()
            try:
                os.chdir(folder)
                Path('build.properties').write_text(PROPS)
                with patch.dict(os.environ, GITHUB_REPOSITORY='owner/repo', GITHUB_SHA='a' * 40, GITHUB_REF='refs/heads/master', VERIFY_ONLY=str(verify).lower()), patch.object(update, 'api', side_effect=responses) as api, patch.object(update, 'output') as output:
                    update.prepare()
                    self.assertEqual(Path('build.properties').read_text(), PROPS)
                    return api.call_count, output.call_args.args[0]
            finally:
                os.chdir(previous)

    def test_verify_only_never_calls_api_or_writes_candidate(self):
        calls, result = self.run_prepare([], verify=True)
        self.assertEqual(calls, 0)
        self.assertEqual(result['changed'], 'false')

    def test_no_update_is_noop(self):
        release = dict(RELEASE, tag_name='6.7.6', html_url='https://github.com/BrowserWorks/waterfox/releases/tag/6.7.6')
        calls, result = self.run_prepare([{'object': {'sha': 'a' * 40}}, release])
        self.assertEqual(calls, 2)
        self.assertEqual(result['build'], 'false')

    def test_duplicate_published_release_is_noop(self):
        calls, result = self.run_prepare([{'object': {'sha': 'a' * 40}}, RELEASE, [{'body': 'Waterfox bootstrap: 6.7.7'}]])
        self.assertEqual(result['build'], 'false')
        self.assertEqual(calls, 3)

    def test_unpublished_candidate_requires_attention(self):
        with self.assertRaisesRegex(ValueError, 'Unpublished candidate'):
            self.run_prepare([{'object': {'sha': 'a' * 40}}, RELEASE, [{'body': 'Waterfox bootstrap: 6.7.7', 'draft': True}]])

    def test_stale_master_fails_before_mutation(self):
        with self.assertRaises(ValueError):
            self.run_prepare([{'object': {'sha': 'b' * 40}}])

    def test_existing_tag_is_never_reused(self):
        with self.assertRaisesRegex(ValueError, 'tag already exists'):
            self.run_prepare([{'object': {'sha': 'a' * 40}}, RELEASE, [], {'object': {'sha': 'b' * 40}}])

    def test_publisher_rejects_foreign_run_before_download(self):
        run = dict(path='.github/workflows/build.yml', conclusion='success', head_branch='master', event='push', head_repository={'full_name': 'owner/repo'})
        with patch.dict(os.environ, GITHUB_REPOSITORY='owner/repo', RELEASE_TAG='1.0.1-3', BUILD_RUN_ID='123'), patch.object(update, 'api', return_value=run), self.assertRaises(ValueError):
            update.publish()

    def test_new_candidate_has_only_allowed_changes(self):
        responses = [{'object': {'sha': 'a' * 40}}, RELEASE,
                     [{'tag_name': '1.0.1-8', 'body': ''}],
                     HTTPError('test', 404, 'missing', {}, None),
                     HTTPError('test', 404, 'missing', {}, None),
                     {'tree': {'sha': 'tree-base'}}, {'sha': 'tree-new'},
                     {'sha': 'c' * 40}, {}]
        with tempfile.TemporaryDirectory() as folder:
            previous = Path.cwd()
            try:
                os.chdir(folder)
                Path('build.properties').write_text(PROPS)
                Path('CHANGELOG.md').write_text('# Changelog\n\nOld entries\n')
                with patch.dict(os.environ, GITHUB_REPOSITORY='owner/repo', GITHUB_SHA='a' * 40, GITHUB_REF='refs/heads/master', VERIFY_ONLY='false'), patch.object(update, 'api', side_effect=responses) as api, patch.object(update, 'output') as output:
                    update.prepare()
                    tree = api.call_args_list[6].args[1]['tree']
                    self.assertEqual({file['path'] for file in tree}, {'build.properties', 'CHANGELOG.md'})
                    self.assertEqual(tree[0]['content'], update.update_properties(PROPS, '6.7.7', 9))
                    self.assertEqual(output.call_args.args[0]['tag'], '1.0.1-9')
                    self.assertEqual(api.call_args_list[7].args[1]['parents'], ['a' * 40])
            finally:
                os.chdir(previous)

    def publish_fixture(self, merged=True, changed_asset=False, failed_stage=None, current=False):
        sha, tag, browser = 'c' * 40, '1.0.1-3', '6.7.7'
        names = ['checksums.txt', f'WaterfoxSetup-{browser}.exe', f'waterfox-portable-win64-{tag}-setup.exe', f'waterfox-portable-win64-{tag}.7z', 'waterfox-portable-win64.exe']
        proof = dict(sha=sha, tag=tag, browser=browser, hashes={name: 'd' * 64 for name in names})
        responses = [dict(path='.github/workflows/daily-waterfox.yml', conclusion='success', head_branch='master', event='schedule', head_repository={'full_name': 'owner/repo'}, head_sha='a' * 40),
                     {'jobs': [dict(name=name, conclusion='failure' if name == failed_stage else 'success') for name in ('test', 'prepare', 'build / build', 'build / release', 'verify')]},
                     {'parents': [{'sha': 'a' * 40}]},
                     {'content': base64.b64encode(update.update_properties(PROPS, browser, 3).encode()).decode()},
                     [dict(merged_at='now' if merged else None, head={'sha': sha}, base={'ref': 'master', 'repo': {'full_name': 'owner/repo'}})],
                     [dict(id=123, tag_name=tag, draft=True, target_commitish=sha, assets=[dict(name=name, state='uploaded', digest='sha256:' + ('e' if changed_asset else 'd') * 64) for name in names])],
                     HTTPError('test', 404, 'missing', {}, None), {}]
        with tempfile.TemporaryDirectory() as folder:
            previous = Path.cwd()
            try:
                os.chdir(folder)
                Path('verified').mkdir()
                Path('verified/verification.json').write_text(json.dumps(proof))
                with patch.dict(os.environ, GITHUB_REPOSITORY='owner/repo', RELEASE_TAG=tag, BUILD_RUN_ID='123', GITHUB_RUN_ID='123', BASE_SHA='a' * 40), patch.object(update, 'api', side_effect=responses) as api, patch('subprocess.run'):
                    update.publish(current_run=current)
                    self.assertEqual(api.call_args.kwargs['method'], 'PATCH')
                    self.assertEqual(api.call_args.args[1]['draft'], False)
            finally:
                os.chdir(previous)

    def test_only_verified_merged_draft_is_published(self):
        self.publish_fixture()

    def test_unmerged_candidate_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'merged first'):
            self.publish_fixture(merged=False)

    def test_changed_release_asset_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'digest changed'):
            self.publish_fixture(changed_asset=True)

    def test_failed_validation_stage_blocks_publication(self):
        for stage in ('test', 'prepare', 'build / build', 'build / release', 'verify'):
            with self.subTest(stage=stage), self.assertRaisesRegex(ValueError, 'validation stage did not succeed'):
                self.publish_fixture(failed_stage=stage)

    def test_automatic_publication_uses_same_verification_gates(self):
        # The current run already has its proof; no second artifact download occurs.
        self.publish_fixture(current=True)

    def merge_fixture(self, stale_base=False, wrong_head=False, refused=False, different_tree=False):
        sha = 'c' * 40
        pr = dict(number=7, mergeable=True, head={'sha': 'd' * 40 if wrong_head else sha, 'repo': {'full_name': 'owner/repo'}}, base={'ref': 'master', 'repo': {'full_name': 'owner/repo'}})
        responses = [{'object': {'sha': 'b' * 40 if stale_base else 'a' * 40}},
                     {'object': {'sha': sha}}, {}, [], pr,
                     pr, {'object': {'sha': 'a' * 40}},
                     {'merged': not refused, 'sha': 'e' * 40},
                     {'tree': {'sha': 'changed' if different_tree else 'tree'}, 'parents': [{'sha': 'a' * 40}, {'sha': sha}]},
                     {'tree': {'sha': 'tree'}}]
        with patch.dict(os.environ, GITHUB_REPOSITORY='owner/repo', CANDIDATE_SHA=sha, BASE_SHA='a' * 40, BROWSER_VERSION='6.7.7', GITHUB_RUN_ID='123'), patch.object(update, 'api', side_effect=responses) as api:
            self.assertEqual(update.merge_candidate(), 'e' * 40)
            self.assertEqual(api.call_args_list[7].args[1]['sha'], sha)
            self.assertEqual(api.call_args_list[7].kwargs['method'], 'PUT')
            self.assertEqual(api.call_args_list[2].args[1]['context'], 'waterfox/verified-update')
            self.assertFalse(any('/reviews' in call.args[0] for call in api.call_args_list))

    def test_exact_candidate_is_merged_without_review_approval(self):
        self.merge_fixture()

    def test_stale_master_blocks_merge(self):
        with self.assertRaisesRegex(ValueError, 'Master changed'):
            self.merge_fixture(stale_base=True)

    def test_replaced_pr_head_blocks_merge(self):
        with self.assertRaisesRegex(ValueError, 'exact verified candidate'):
            self.merge_fixture(wrong_head=True)

    def test_refused_merge_blocks_release(self):
        with self.assertRaisesRegex(ValueError, 'not merged'):
            self.merge_fixture(refused=True)

    def test_raced_merge_tree_blocks_release(self):
        with self.assertRaisesRegex(ValueError, 'Merged tree differs'):
            self.merge_fixture(different_tree=True)

    def test_automatic_order_and_failure_gate(self):
        with patch.dict(os.environ, GITHUB_RUN_ID='123'), patch.object(update, 'draft', side_effect=ValueError('verification failed')), patch.object(update, 'merge_candidate') as merge, patch.object(update, 'publish') as publish:
            with self.assertRaises(ValueError):
                update.automatic()
            merge.assert_not_called()
            publish.assert_not_called()


if __name__ == '__main__':
    unittest.main()
