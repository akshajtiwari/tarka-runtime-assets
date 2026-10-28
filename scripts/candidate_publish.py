"""Create a new prerelease at the verified build commit; never replace a release."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from candidate_files import verify_candidate


def github_request(method, path, body=None):
    command = ['gh', 'api', '--include', '--method', method, path]
    data = None
    if body is not None:
        command.extend(['--input', '-'])
        data = json.dumps(body)
    result = subprocess.run(command, input=data, capture_output=True, text=True)
    response = result.stdout.replace('\r\n', '\n')
    header, separator, payload = response.partition('\n\n')
    match = re.match(r'HTTP/\S+ (\d{3})\b', header)
    if not separator or not match:
        raise RuntimeError('GitHub API returned no usable status; publication stopped.')
    status = int(match[1])
    if result.returncode and status != 404:
        raise RuntimeError('GitHub API failed; publication stopped (HTTP ' + str(status) + ').')
    return status, json.loads(payload)


def require_new_release(repository, version):
    for path in ('git/ref/tags/' + version, 'releases/tags/' + version):
        status, unused = github_request('GET', f'repos/{repository}/' + path)
        if status == 200:
            raise ValueError('Candidate tag or release already exists; refusing to overwrite it.')
        if status != 404:
            raise RuntimeError('Could not prove candidate tag and release are absent.')
    # REST's release-by-tag endpoint omits pending drafts, which can exist without a tag.
    owner, name = repository.split('/')
    query = '''query($owner: String!, $name: String!, $tag: String!) {
      repository(owner: $owner, name: $name) { release(tagName: $tag) { tagName isDraft } }
    }'''
    status, result = github_request('POST', 'graphql',
                                  {'query': query, 'variables': {'owner': owner, 'name': name, 'tag': version}})
    if status != 200 or not isinstance(result, dict) or result.get('errors'):
        raise RuntimeError('Could not prove candidate draft release is absent.')
    data = result.get('data')
    source = data.get('repository') if isinstance(data, dict) else None
    if not isinstance(source, dict) or 'release' not in source:
        raise RuntimeError('Could not prove candidate draft release is absent.')
    release = source['release']
    if release is None:
        return
    if not isinstance(release, dict) or release.get('tagName') != version:
        raise RuntimeError('Candidate release lookup was ambiguous; publication stopped.')
    raise ValueError('Candidate tag or release already exists; refusing to overwrite it.')


def write_notes(path, repository, version, run_id, commit):
    text = f'''TARKA tool-pack candidate {version}

ARM64 execution remains unverified. App release acceptance is pending.
This prerelease supports tool-pack installation and recovery testing.

- Build: https://github.com/{repository}/actions/runs/{run_id}
- Exact source commit: https://github.com/{repository}/tree/{commit}
- Includes eight runtime packs, corresponding sources, licenses and SHA256SUMS.
- Every published file passed the flat allowlist, integrity and provenance checks.
'''
    path.write_text(text)


def publish_candidate(folder, repository, version, run_id, commit, notes):
    files = verify_candidate(folder, repository, version, run_id, commit)
    require_new_release(repository, version)
    write_notes(notes, repository, version, run_id, commit)
    # Creating the ref separately fails atomically if another publication took this tag.
    status, record = github_request('POST', f'repos/{repository}/git/refs',
                                    {'ref': 'refs/tags/' + version, 'sha': commit})
    if status != 201 or record.get('object', {}).get('sha') != commit:
        raise RuntimeError('Could not create the candidate tag at the verified build commit.')
    command = ['gh', 'release', 'create', version, '--repo', repository, '--verify-tag',
               '--target', commit, '--draft', '--prerelease', '--latest=false',
               '--title', 'TARKA tool-pack candidate ' + version + ' (ARM execution unverified)',
               '--notes-file', str(notes), *[str(file.resolve()) for file in files]]
    subprocess.run(command, check=True)
    status, record = github_request('GET', f'repos/{repository}/git/ref/tags/{version}')
    if status != 200 or record.get('object', {}).get('sha') != commit:
        raise RuntimeError('Candidate tag changed; leaving the release as a draft.')
    subprocess.run(['gh', 'release', 'edit', version, '--repo', repository, '--verify-tag',
                    '--draft=false', '--prerelease', '--latest=false'], check=True)


if __name__ == '__main__':
    publish_candidate(Path(sys.argv[1]), os.environ['ASSET_REPOSITORY'], os.environ['BUILD_VERSION'],
                      os.environ['BUILD_RUN_ID'], os.environ['BUILD_COMMIT'], Path('.artifacts/candidate-notes.md'))
