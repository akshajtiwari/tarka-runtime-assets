from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
from candidate_build_fixtures import COMMIT, REPOSITORY, RUN_ID, VERSION
from candidate_publish import github_request, publish_candidate

ABSENT_DRAFT = (200, {'data': {'repository': {'release': None}}})


class CandidatePublicationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)
        self.notes = self.folder / 'notes.md'
        self.files = [self.folder / 'runtime.zip']
        self.verifier = patch('candidate_publish.verify_candidate', return_value=self.files)
        self.verifier.start()
        self.addCleanup(self.verifier.stop)

    def publish(self):
        publish_candidate(self.folder, REPOSITORY, VERSION, RUN_ID, COMMIT, self.notes)

    def test_existing_tag_or_release_is_never_overwritten(self):
        for responses in [[(200, {})], [(404, {}), (200, {})]]:
            with patch('candidate_publish.github_request', side_effect=responses) as api:
                with patch('candidate_publish.subprocess.run') as command:
                    with self.assertRaisesRegex(ValueError, 'already exists'):
                        self.publish()
                command.assert_not_called()
                self.assertTrue(all(call.args[0] == 'GET' for call in api.call_args_list))

    def test_tag_creation_race_cannot_fall_back_to_the_latest_branch(self):
        with patch('candidate_publish.github_request', side_effect=[(404, {}), (404, {}), ABSENT_DRAFT, (422, {})]):
            with patch('candidate_publish.subprocess.run') as command:
                with self.assertRaisesRegex(RuntimeError, 'verified build commit'):
                    self.publish()
            command.assert_not_called()

    def test_exact_build_tag_draft_upload_and_prerelease_use_structured_notes(self):
        record = {'object': {'sha': COMMIT}}
        responses = [(404, {}), (404, {}), ABSENT_DRAFT, (201, record), (200, record)]
        with patch('candidate_publish.github_request', side_effect=responses) as api:
            with patch('candidate_publish.subprocess.run') as command:
                self.publish()
        self.assertEqual(api.call_args_list[2].args[:2], ('POST', 'graphql'))
        self.assertEqual(api.call_args_list[2].args[2]['variables'],
                         {'owner': 'owner', 'name': 'assets', 'tag': VERSION})
        self.assertEqual(api.call_args_list[3].args[2], {'ref': 'refs/tags/' + VERSION, 'sha': COMMIT})
        create, publish = [call.args[0] for call in command.call_args_list]
        for flag in ['--draft', '--prerelease', '--verify-tag', '--latest=false']:
            self.assertIn(flag, create)
        self.assertEqual(create[create.index('--target') + 1], COMMIT)
        self.assertEqual(create[create.index('--notes-file') + 1], str(self.notes))
        self.assertIn('--draft=false', publish)
        self.assertIn('--prerelease', publish)
        self.assertIn('--latest=false', publish)
        self.assertIn('ARM64 execution remains unverified.', self.notes.read_text())
        self.assertIn('\n\n', self.notes.read_text())

    def test_failed_upload_or_changed_tag_never_publishes_the_draft(self):
        record = {'object': {'sha': COMMIT}}
        with patch('candidate_publish.github_request', side_effect=[(404, {}), (404, {}), ABSENT_DRAFT, (201, record)]):
            with patch('candidate_publish.subprocess.run', side_effect=subprocess.CalledProcessError(1, 'gh')) as command:
                with self.assertRaises(subprocess.CalledProcessError):
                    self.publish()
                self.assertEqual(command.call_count, 1)
        responses = [(404, {}), (404, {}), ABSENT_DRAFT, (201, record), (200, {'object': {'sha': 'b' * 40}})]
        with patch('candidate_publish.github_request', side_effect=responses):
            with patch('candidate_publish.subprocess.run') as command:
                with self.assertRaisesRegex(RuntimeError, 'tag changed'):
                    self.publish()
                self.assertEqual(command.call_count, 1)

    def test_pending_draft_without_a_tag_is_refused_before_any_tag_or_release_mutation(self):
        for draft in (True, False):
            release = {'tagName': VERSION, 'isDraft': draft}
            responses = [(404, {}), (404, {}), (200, {'data': {'repository': {'release': release}}})]
            with patch('candidate_publish.github_request', side_effect=responses) as api:
                with patch('candidate_publish.subprocess.run') as command:
                    with self.assertRaisesRegex(ValueError, 'already exists'):
                        self.publish()
                command.assert_not_called()
                self.assertEqual(api.call_count, 3)
                self.assertEqual(api.call_args_list[-1].args[:2], ('POST', 'graphql'))

    def test_draft_lookup_errors_or_ambiguous_responses_fail_closed(self):
        cases = [(403, {}), (200, {'errors': [{'message': 'permission denied'}]}),
                 (200, {'errors': [{'message': 'partial data'}], 'data': {'repository': {'release': None}}}),
                 (200, {'data': None}), (200, {'data': {'repository': None}}),
                 (200, {'data': {'repository': {}}}), (200, []),
                 (200, {'data': {'repository': {'release': 'unknown'}}}),
                 (200, {'data': {'repository': {'release': {'tagName': 'other'}}}})]
        for response in cases:
            with self.subTest(response=response):
                with patch('candidate_publish.github_request', side_effect=[(404, {}), (404, {}), response]) as api:
                    with patch('candidate_publish.subprocess.run') as command:
                        with self.assertRaises(RuntimeError):
                            self.publish()
                    command.assert_not_called()
                    self.assertEqual(api.call_count, 3)

    def test_only_an_actual_404_proves_absence(self):
        response = subprocess.CompletedProcess([], 1, 'HTTP/2.0 404 Not Found\nX-Test: true\n\n{}', 'not found')
        with patch('candidate_publish.subprocess.run', return_value=response):
            self.assertEqual(github_request('GET', 'public/path'), (404, {}))
        for status, stdout in [(1, ''), (1, 'HTTP/2.0 403 Forbidden\n\n{}'), (0, 'not JSON')]:
            response = subprocess.CompletedProcess([], status, stdout, 'network or permission failure')
            with patch('candidate_publish.subprocess.run', return_value=response):
                with self.subTest(stdout=stdout), self.assertRaises(RuntimeError):
                    github_request('GET', 'public/path')


if __name__ == '__main__':
    unittest.main()
