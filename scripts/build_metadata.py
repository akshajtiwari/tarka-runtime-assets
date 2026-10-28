"""Record the public build revision without exposing workflow credentials."""
import json
import os
from pathlib import Path
import re


def main():
    repository = os.environ['ASSET_REPOSITORY']
    commit = os.environ['ASSET_COMMIT']
    version = os.environ['PACK_VERSION']
    run_id = os.environ['ASSET_RUN_ID']
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository):
        raise ValueError('Invalid public source repository.')
    if not re.fullmatch('[0-9a-f]{40}', commit) or not run_id.isdigit():
        raise ValueError('Invalid source revision or workflow run.')
    record = {'repository': repository, 'commit': commit, 'version': version,
              'buildUrl': f'https://github.com/{repository}/actions/runs/{run_id}',
              'sourceUrl': f'https://github.com/{repository}/tree/{commit}'}
    Path('.artifacts/release/build-source.json').write_text(json.dumps(record, indent=2) + '\n')


if __name__ == '__main__':
    main()
