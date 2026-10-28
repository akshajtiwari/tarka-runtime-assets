"""Accept only successful public main-branch builds and their exact release artifact."""
import json
import os
from pathlib import Path
import re
import sys


def validate_inputs(repository, version, run_id):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository):
        raise ValueError('Invalid asset repository.')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,63}', version):
        raise ValueError('Invalid candidate version.')
    if '..' in version or version.endswith(('.', '.lock')):
        raise ValueError('Candidate version is not a valid immutable tag.')
    if not re.fullmatch(r'[1-9][0-9]{0,19}', run_id):
        raise ValueError('Invalid build run ID.')


def validate_build(run, repository, run_id):
    expected = {'id': int(run_id), 'event': 'workflow_dispatch', 'head_branch': 'main',
                'path': '.github/workflows/build-assets.yml', 'status': 'completed',
                'conclusion': 'success'}
    if any(run.get(key) != value for key, value in expected.items()):
        raise ValueError('Candidate requires a successful manual build-assets.yml run on main.')
    for key in ('repository', 'head_repository'):
        source = run.get(key) or {}
        if source.get('full_name') != repository or source.get('private') is not False:
            raise ValueError('Build must belong to this same public asset repository.')
    commit = run.get('head_sha', '')
    if not re.fullmatch('[0-9a-f]{40}', commit):
        raise ValueError('Build commit is invalid.')
    return commit


def validate_artifact_list(record, version, run_id, commit):
    artifacts = record['artifacts']
    if record['total_count'] != len(artifacts):
        raise ValueError('Build artifact listing is incomplete.')
    matches = [item for item in artifacts if item['name'] == 'runtime-release-' + version]
    if len(matches) != 1 or matches[0].get('expired') is not False:
        raise ValueError('Expected exactly one available release artifact for this version.')
    artifact = matches[0]
    source = artifact.get('workflow_run') or {}
    if source.get('id') != int(run_id) or source.get('head_sha') != commit:
        raise ValueError('Artifact belongs to a different build.')
    if type(artifact.get('id')) is not int or artifact['id'] <= 0:
        raise ValueError('Artifact ID is invalid.')
    return artifact['id']


def validate_provenance(record, repository, version, run_id, commit):
    expected = {'repository': repository, 'version': version, 'commit': commit,
                'buildUrl': f'https://github.com/{repository}/actions/runs/{run_id}',
                'sourceUrl': f'https://github.com/{repository}/tree/{commit}'}
    if record != expected:
        raise ValueError('Release provenance differs from the selected build.')


def main():
    repository = os.environ['ASSET_REPOSITORY']
    version = os.environ['BUILD_VERSION']
    run_id = os.environ['BUILD_RUN_ID']
    validate_inputs(repository, version, run_id)
    if len(sys.argv) == 1:
        return
    run = json.loads(Path(sys.argv[1]).read_text())
    commit = validate_build(run, repository, run_id)
    artifacts = json.loads(Path(sys.argv[2]).read_text())
    artifact_id = validate_artifact_list(artifacts, version, run_id, commit)
    with Path(os.environ['GITHUB_OUTPUT']).open('a') as output:
        output.write(f'commit={commit}\nartifact_id={artifact_id}\n')


if __name__ == '__main__':
    main()
