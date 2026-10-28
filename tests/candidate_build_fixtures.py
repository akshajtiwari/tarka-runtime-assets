REPOSITORY = 'owner/assets'
VERSION = 'test.1'
RUN_ID = '123'
COMMIT = 'a' * 40


def build_record():
    return {'id': int(RUN_ID), 'event': 'workflow_dispatch', 'head_branch': 'main',
            'path': '.github/workflows/build-assets.yml', 'status': 'completed',
            'conclusion': 'success', 'head_sha': COMMIT,
            'repository': {'full_name': REPOSITORY, 'private': False},
            'head_repository': {'full_name': REPOSITORY, 'private': False}}


def artifact_record():
    return {'total_count': 1, 'artifacts': [{'id': 456, 'name': 'runtime-release-' + VERSION,
            'expired': False, 'workflow_run': {'id': int(RUN_ID), 'head_sha': COMMIT}}]}
