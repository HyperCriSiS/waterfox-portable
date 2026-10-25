"""Narrow, fail-closed update planning. No upstream code is imported."""
import base64
import datetime
import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path


def version(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:\.[0-9]+)?", value):
        raise ValueError("Invalid stable Waterfox version")
    parts = tuple(map(int, value.split('.')))
    if any(part > 65535 for part in parts):
        raise ValueError("Version component out of range")
    return parts + (0,) * (4 - len(parts))


def stable_release(data):
    if data.get('draft') is not False or data.get('prerelease') is not False:
        raise ValueError('Only stable upstream releases are allowed')
    value = data['tag_name']
    version(value)
    if data.get('html_url', '').lower() != f'https://github.com/browserworks/waterfox/releases/tag/{value}'.lower():
        raise ValueError('Unexpected upstream release source')
    return value


def property_value(text, key):
    matches = re.findall(r'^' + re.escape(key) + r'[ \t]*=[ \t]*(\S+)[ \t]*$', text, re.M)
    if len(matches) != 1:
        raise ValueError(f'Missing or duplicate property: {key}')
    return matches[0]


def update_properties(text, browser, revision):
    if version(browser) <= version(property_value(text, 'waterfox.version')):
        raise ValueError('Updates must increase the browser version')
    if not isinstance(revision, int) or revision <= int(property_value(text, 'app.release')) or revision > 65535:
        raise ValueError('Invalid package revision')
    for key, value in [('waterfox.version', browser), ('app.release', str(revision))]:
        text = re.sub(r'^' + re.escape(key) + r'[ \t]*=[ \t]*\S+[ \t]*$', key + ' = ' + value, text, flags=re.M)
    return text


def api(path, data=None, method=None):
    request = urllib.request.Request('https://api.github.com/' + path,
        data=json.dumps(data).encode() if data is not None else None,
        headers={'Authorization': 'Bearer ' + os.environ['GH_TOKEN'],
                 'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'},
        method=method)
    with urllib.request.urlopen(request, timeout=60) as response:
        body = response.read()
        return json.loads(body) if body else None


def contents(repo, path, sha):
    data = api(f'repos/{repo}/contents/{path}?ref={sha}')
    return base64.b64decode(data['content']).decode().replace('\r\n', '\n')


def all_releases(repo):
    result = []
    page = 1
    while True:
        batch = api(f'repos/{repo}/releases?per_page=100&page={page}')
        result.extend(batch)
        if len(batch) < 100:
            return result
        page += 1


def optional_ref(repo, ref):
    try:
        return api(f'repos/{repo}/git/ref/{ref}')
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise
        error.close()
        return None


def output(values):
    with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as stream:
        for key, value in values.items():
            stream.write(f'{key}={value}\n')


def prepare():
    repo = os.environ['GITHUB_REPOSITORY']
    base = os.environ['GITHUB_SHA']
    text = Path('build.properties').read_text(encoding='utf-8')
    browser = property_value(text, 'waterfox.version')
    launcher = property_value(text, 'app.version')
    version(browser)
    if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', launcher):
        raise ValueError('Invalid launcher version')
    revision = int(property_value(text, 'app.release'))
    if os.environ.get('VERIFY_ONLY') == 'true':
        output(dict(build='true', changed='false', sha=base, base=base,
                    tag=f'{launcher}-{revision}', browser=browser))
        return
    if os.environ['GITHUB_REF'] != 'refs/heads/master':
        raise ValueError('Updates can only start on master')
    if api(f'repos/{repo}/git/ref/heads/master')['object']['sha'] != base:
        raise ValueError('Master changed; retry with the current revision')
    latest = stable_release(api('repos/BrowserWorks/Waterfox/releases/latest'))
    if version(latest) <= version(browser):
        output(dict(build='false', changed='false'))
        return
    releases = all_releases(repo)
    marker = f'Waterfox bootstrap: {latest}'
    matching_releases = [release for release in releases if marker in (release.get('body') or '').splitlines()]
    if any(release.get('draft') for release in matching_releases):
        raise ValueError('Unpublished candidate exists; inspect the failed release run')
    if matching_releases:
        output(dict(build='false', changed='false'))
        return
    for release in releases:
        match = re.fullmatch(re.escape(launcher) + r'-(\d+)', release['tag_name'])
        if match:
            revision = max(revision, int(match[1]))
    revision += 1
    updated = update_properties(text, latest, revision)
    tag = f'{launcher}-{revision}'
    branch = f'automation/waterfox-{latest}'
    if optional_ref(repo, 'tags/' + tag):
        raise ValueError('Release tag already exists; never reuse tags')
    # An existing branch is deliberately never overwritten, even after a failed run.
    try:
        api(f'repos/{repo}/git/ref/heads/{branch}')
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise
        error.close()
    else:
        raise ValueError('Candidate branch already exists; inspect the previous run')
    commit = api(f'repos/{repo}/git/commits/{base}')
    changelog = Path('CHANGELOG.md').read_text(encoding='utf-8')
    entry = (f'## {tag} ({datetime.date.today().isoformat()})\n\n'
             f'* {marker}. Launcher code and privacy defaults are unchanged.\n\n')
    changelog = changelog.replace('# Changelog\n\n', '# Changelog\n\n' + entry, 1)
    tree = api(f'repos/{repo}/git/trees', {'base_tree': commit['tree']['sha'], 'tree': [
        {'path': 'build.properties', 'mode': '100644', 'type': 'blob', 'content': updated},
        {'path': 'CHANGELOG.md', 'mode': '100644', 'type': 'blob', 'content': changelog}]})
    candidate = api(f'repos/{repo}/git/commits', {'message': f'Update Waterfox bootstrap to {latest}',
                    'tree': tree['sha'], 'parents': [base]})
    api(f'repos/{repo}/git/refs', {'ref': f'refs/heads/{branch}', 'sha': candidate['sha']})
    output(dict(build='true', changed='true', sha=candidate['sha'], base=base,
                tag=tag, browser=latest, branch=branch))


def draft():
    repo = os.environ['GITHUB_REPOSITORY']
    sha, base = os.environ['CANDIDATE_SHA'], os.environ['BASE_SHA']
    tag, browser = os.environ['RELEASE_TAG'], os.environ['BROWSER_VERSION']
    branch = 'automation/waterfox-' + browser
    version(browser)
    if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+-[0-9]+', tag):
        raise ValueError('Invalid release tag')
    if api(f'repos/{repo}/git/ref/heads/master')['object']['sha'] != base:
        raise ValueError('Master changed during validation; refuse stale draft')
    if api(f'repos/{repo}/git/ref/heads/{branch}')['object']['sha'] != sha:
        raise ValueError('Candidate branch changed')
    if optional_ref(repo, 'tags/' + tag):
        raise ValueError('Release tag already exists; refuse to overwrite')
    diff = api(f'repos/{repo}/compare/{base}...{sha}')
    if diff['ahead_by'] != 1 or diff['behind_by'] != 0 or {f['filename'] for f in diff['files']} != {'build.properties', 'CHANGELOG.md'}:
        raise ValueError('Candidate contains unexpected changes')
    old = contents(repo, 'build.properties', base)
    if contents(repo, 'build.properties', sha) != update_properties(old, browser, int(tag.rsplit('-', 1)[1])):
        raise ValueError('Candidate properties differ from the allowed update')
    if property_value(old, 'app.version') != tag.rsplit('-', 1)[0]:
        raise ValueError('Launcher version changed')
    checks = api(f'repos/{repo}/commits/{base}/check-runs?per_page=100')['check_runs']
    for name in ('Analyze (go)', 'Analyze (actions)', 'run / zizmor'):
        matching = [check for check in checks if check['name'] == name]
        if not matching or matching[0]['conclusion'] != 'success' or matching[0]['app']['slug'] != 'github-actions':
            raise ValueError(f'Trusted base security check not successful: {name}')
    proof = json.loads(Path('verified/verification.json').read_text())
    validate_proof(proof, sha, tag, browser)
    files = Path('release')
    import hashlib
    if {p.name for p in files.iterdir()} != set(proof['hashes']):
        raise ValueError('Unexpected release files')
    for name, digest in proof['hashes'].items():
        if hashlib.sha256((files / name).read_bytes()).hexdigest() != digest:
            raise ValueError('Release artifact changed after verification')
    notes = (f'Waterfox bootstrap: {browser}\n\n'
             f'Validated candidate `{sha}` from base `{base}`.\n'
             f'Build and verification: https://github.com/{repo}/actions/runs/{os.environ["GITHUB_RUN_ID"]}\n\n'
             'Windows signature, archive integrity, SHA256 hashes, fresh and existing portable profile starts passed. '
             'Browser self-updates and privacy defaults are retained.\n\n'
             'Automatically merged and published only after all required validation stages pass.\n')
    # gh creates a draft and uploads the exact files verified above. Never clobber assets.
    Path('release-notes.md').write_text(notes, encoding='utf-8')
    import subprocess
    subprocess.run(['gh', 'release', 'create', tag, *map(str, sorted(files.iterdir())),
        '--repo', repo, '--target', sha, '--title', tag, '--draft',
        '--notes-file', 'release-notes.md'], check=True)


def validate_proof(proof, sha, tag, browser):
    if proof.get('sha') != sha or proof.get('tag') != tag or proof.get('browser') != browser:
        raise ValueError('Verification belongs to another candidate')
    expected = {'checksums.txt', f'WaterfoxSetup-{browser}.exe',
                f'waterfox-portable-win64-{tag}-setup.exe', f'waterfox-portable-win64-{tag}.7z',
                'waterfox-portable-win64.exe'}
    if set(proof.get('hashes', {})) != expected or any(not re.fullmatch(r'[a-f0-9]{64}', value) for value in proof['hashes'].values()):
        raise ValueError('Invalid verification file manifest')


def merge_candidate():
    """Merge only this run's already verified candidate, never approve a review."""
    repo = os.environ['GITHUB_REPOSITORY']
    sha, base = os.environ['CANDIDATE_SHA'], os.environ['BASE_SHA']
    browser = os.environ['BROWSER_VERSION']
    version(browser)
    branch = 'automation/waterfox-' + browser
    if api(f'repos/{repo}/git/ref/heads/master')['object']['sha'] != base:
        raise ValueError('Master changed before merge')
    if api(f'repos/{repo}/git/ref/heads/{branch}')['object']['sha'] != sha:
        raise ValueError('Candidate changed before merge')
    api(f'repos/{repo}/statuses/{sha}', {'state': 'success', 'context': 'waterfox/verified-update',
        'description': 'Signed package, profile and safety validation passed',
        'target_url': f'https://github.com/{repo}/actions/runs/{os.environ["GITHUB_RUN_ID"]}'})
    pulls = api(f'repos/{repo}/pulls?state=open&base=master&head={repo.split("/")[0]}:{branch}')
    if not pulls:
        pulls = [api(f'repos/{repo}/pulls', {'title': f'Update Waterfox bootstrap to {browser}',
            'head': branch, 'base': 'master',
            'body': f'Automated version-only update. All package and safety tests passed in https://github.com/{repo}/actions/runs/{os.environ["GITHUB_RUN_ID"]}. No launcher code or workflow changes.'})]
    if (len(pulls) != 1 or pulls[0]['head']['sha'] != sha or pulls[0]['base']['ref'] != 'master'
            or pulls[0]['head']['repo']['full_name'].lower() != repo.lower()
            or pulls[0]['base']['repo']['full_name'].lower() != repo.lower()):
        raise ValueError('PR does not identify the exact verified candidate')
    result = api(f'repos/{repo}/pulls/{pulls[0]["number"]}/merge',
                 {'sha': sha, 'merge_method': 'merge'}, method='PUT')
    if result.get('merged') is not True:
        raise ValueError('Candidate PR was not merged')
    merged = api(f'repos/{repo}/git/commits/{result["sha"]}')
    candidate = api(f'repos/{repo}/git/commits/{sha}')
    if merged['tree']['sha'] != candidate['tree']['sha'] or sha not in [parent['sha'] for parent in merged['parents']]:
        raise ValueError('Merged tree differs from the tested candidate; refuse publication')
    return result['sha']


def automatic():
    # Draft validation checks the exact allowed diff, base security checks and package proof
    # before the first PR/merge operation. The draft remains private if a later gate fails.
    draft()
    merge_candidate()
    os.environ['BUILD_RUN_ID'] = os.environ['GITHUB_RUN_ID']
    publish(current_run=True)


def publish(current_run=False):
    """Publish only verified files whose exact candidate PR was merged."""
    repo, tag = os.environ['GITHUB_REPOSITORY'], os.environ['RELEASE_TAG']
    run_id = os.environ['BUILD_RUN_ID']
    if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+-[0-9]+', tag) or not re.fullmatch(r'[0-9]+', run_id):
        raise ValueError('Invalid release input')
    run = api(f'repos/{repo}/actions/runs/{run_id}')
    if (run['path'] != '.github/workflows/daily-waterfox.yml'
            or run['head_branch'] != 'master' or run['event'] not in ('schedule', 'workflow_dispatch')
            or run['head_repository']['full_name'].lower() != repo.lower()):
        raise ValueError('Not a successful trusted daily update run')
    if current_run:
        if run_id != os.environ['GITHUB_RUN_ID'] or run['head_sha'] != os.environ['BASE_SHA']:
            raise ValueError('Automatic publication must belong to this run and base')
    elif run['conclusion'] not in ('success', 'failure'):
        raise ValueError('Originating run must have finished')
    jobs = api(f'repos/{repo}/actions/runs/{run_id}/jobs?per_page=100')['jobs']
    for name in ('test', 'prepare', 'build / build', 'build / release', 'verify'):
        matching = [job for job in jobs if job['name'] == name]
        if not matching or any(job['conclusion'] != 'success' for job in matching):
            raise ValueError(f'Required validation stage did not succeed: {name}')
    import subprocess
    if not current_run:
        subprocess.run(['gh', 'run', 'download', run_id, '--repo', repo,
                        '--name', 'verified-waterfox', '--dir', 'verified'], check=True)
    proof = json.loads(Path('verified/verification.json').read_text())
    validate_proof(proof, proof['sha'], tag, proof['browser'])
    if not re.fullmatch(r'[a-f0-9]{40}', proof['sha']):
        raise ValueError('Invalid candidate SHA')
    version(proof['browser'])
    candidate = api(f'repos/{repo}/git/commits/{proof["sha"]}')
    if [parent['sha'] for parent in candidate['parents']] != [run['head_sha']]:
        raise ValueError('Candidate not derived from verified run base')
    props = contents(repo, 'build.properties', proof['sha'])
    if (property_value(props, 'waterfox.version') != proof['browser']
            or property_value(props, 'app.version') + '-' + property_value(props, 'app.release') != tag):
        raise ValueError('Release metadata mismatch')
    pulls = api(f'repos/{repo}/commits/{proof["sha"]}/pulls')
    if not any(pr['merged_at'] and pr['head']['sha'] == proof['sha'] and pr['base']['ref'] == 'master'
               and pr['base']['repo']['full_name'].lower() == repo.lower() for pr in pulls):
        raise ValueError('The exact candidate PR must be merged first')
    # Drafts may not have a git tag yet; the published-by-tag endpoint is unsuitable.
    matching = [release for release in all_releases(repo) if release['tag_name'] == tag]
    if len(matching) != 1:
        raise ValueError('Expected exactly one draft release')
    release = matching[0]
    if release['draft'] is not True or release['target_commitish'] != proof['sha']:
        raise ValueError('Not the verified draft release')
    if {asset['name'] for asset in release['assets']} != set(proof['hashes']):
        raise ValueError('Release asset set changed')
    for asset in release['assets']:
        if asset['state'] != 'uploaded' or asset.get('digest') != 'sha256:' + proof['hashes'][asset['name']]:
            raise ValueError('Release asset digest changed')
    existing_tag = optional_ref(repo, 'tags/' + tag)
    if existing_tag and (existing_tag['object']['type'] != 'commit' or existing_tag['object']['sha'] != proof['sha']):
        raise ValueError('Existing tag does not identify the verified candidate')
    api(f'repos/{repo}/releases/{release["id"]}', {'draft': False, 'make_latest': 'true'}, method='PATCH')


if __name__ == '__main__':
    import sys
    {'prepare': prepare, 'automatic': automatic, 'publish': publish}[sys.argv[1]]()
