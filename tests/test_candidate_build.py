import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
from candidate_build_fixtures import COMMIT, REPOSITORY, RUN_ID, VERSION, artifact_record, build_record
from candidate_build import validate_artifact_list, validate_build, validate_inputs


class CandidateBuildTests(unittest.TestCase):
    def test_only_the_selected_successful_public_build_is_accepted(self):
        self.assertEqual(validate_build(build_record(), REPOSITORY, RUN_ID), COMMIT)
        changes = {'id': 999, 'event': 'push', 'head_branch': 'feature',
                   'path': '.github/workflows/other.yml', 'status': 'in_progress',
                   'conclusion': 'failure', 'head_sha': 'not-a-commit'}
        for key, value in changes.items():
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_build(dict(build_record(), **{key: value}), REPOSITORY, RUN_ID)
        for key in ('repository', 'head_repository'):
            for source in ({'full_name': 'owner/private-app', 'private': False},
                           {'full_name': REPOSITORY, 'private': True}, None):
                with self.subTest(key=key, source=source), self.assertRaises(ValueError):
                    validate_build(dict(build_record(), **{key: source}), REPOSITORY, RUN_ID)

    def test_artifact_identity_duplicates_expiry_and_pagination_fail_closed(self):
        self.assertEqual(validate_artifact_list(artifact_record(), VERSION, RUN_ID, COMMIT), 456)
        cases = []
        for key, value in [('name', 'runtime-release-other'), ('expired', True), ('id', True)]:
            record = artifact_record()
            record['artifacts'][0][key] = value
            cases.append(record)
        duplicate = artifact_record()
        duplicate['artifacts'] *= 2
        duplicate['total_count'] = 2
        cases.append(duplicate)
        incomplete = artifact_record()
        incomplete['total_count'] = 2
        cases.append(incomplete)
        for key, value in [('id', 999), ('head_sha', 'b' * 40)]:
            record = artifact_record()
            record['artifacts'][0]['workflow_run'][key] = value
            cases.append(record)
        for record in cases:
            with self.subTest(record=record), self.assertRaises(ValueError):
                validate_artifact_list(copy.deepcopy(record), VERSION, RUN_ID, COMMIT)

    def test_inputs_cannot_change_api_paths_or_create_invalid_tags(self):
        validate_inputs(REPOSITORY, VERSION, RUN_ID)
        for repository, version, run_id in [('owner/assets/other', VERSION, RUN_ID),
                (REPOSITORY, 'v1/other', RUN_ID), (REPOSITORY, 'v1..2', RUN_ID),
                (REPOSITORY, 'v1.lock', RUN_ID), (REPOSITORY, 'v1.', RUN_ID),
                (REPOSITORY, VERSION, '../../other'), (REPOSITORY, VERSION, '0')]:
            with self.subTest(version=version, run_id=run_id), self.assertRaises(ValueError):
                validate_inputs(repository, version, run_id)


if __name__ == '__main__':
    unittest.main()
