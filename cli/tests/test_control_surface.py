"""Exercise the compiled Rust/Python boundary without provider calls. Apache-2.0."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
BINARY = Path(os.environ.get('RECEIPTS_CLI', ROOT / 'target/debug/receipts')).resolve()
STUB = '''import json, os, sys
print(json.dumps({"args": sys.argv[1:], "key_present": "OPENAI_API_KEY" in os.environ,
                  "isolated": sys.flags.isolated, "no_site": sys.flags.no_site,
                  "cwd": os.getcwd()}), flush=True)
print("fixture diagnostic", file=sys.stderr)
if os.environ.get("RECEIPTS_TEST_SIGNAL"):
    import signal
    os.kill(os.getpid(), signal.SIGTERM)
sys.exit(int(os.environ.get("RECEIPTS_TEST_EXIT", "0")))
'''


class ControlSurfaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='receipts cli ')
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.env = os.environ.copy()
        self.env.pop('OPENAI_API_KEY', None)
        self.env.pop('RECEIPTS_TEST_EXIT', None)
        self.env.pop('RECEIPTS_TEST_SIGNAL', None)

    def call(self, args, *, root=ROOT, cwd=None, env=None, python=sys.executable):
        return subprocess.run([str(BINARY), '--root', str(root), '--python', python, *args],
                              cwd=cwd or self.work, env=env or self.env,
                              capture_output=True, text=True, timeout=30)

    def fake_checkout(self):
        root = self.work / 'checkout with spaces'
        pkg = root / 'src/receipts'
        pkg.mkdir(parents=True)
        (pkg / '__init__.py').write_text('')
        for name in ('__main__.py', 'runner.py', 'action_review.py', 'experiment.py'):
            (pkg / name).write_text(STUB)
        folder = root / 'experiments/preservation-2026-10-30'
        folder.mkdir(parents=True)
        (folder / 'verify.py').write_text(STUB)
        return root

    def direct(self, args):
        source = str(ROOT / 'src')
        bootstrap = 'import sys,runpy; sys.path.insert(0,sys.argv.pop(1)); runpy.run_module("receipts",run_name="__main__")'
        return subprocess.run([sys.executable, '-I', '-S', '-c', bootstrap, source, *args],
                              cwd=self.work, env=self.env, capture_output=True, text=True, timeout=30)

    def test_all_metadata_commands_preserve_python_json(self):
        capture = self.work / 'capture;$(touch UNEXPECTED).txt'
        capture.write_text('public synthetic capture\n')
        commands = [
            ['snowflake', '1273816504776982529'],
            ['utc', '2026-09-01T00:30:00+09:30'],
            ['style', str(ROOT / 'examples/posts.json')],
            ['funding', str(ROOT / 'examples/funding.json'), '--payer', 'donor-d', '--payee', 'person-p'],
            ['receipt', str(capture), '--url', 'https://example.invalid/capture',
             '--retrieved-at', '2026-10-30T00:00:00Z', '--locator', 'line 1; $(touch UNEXPECTED)',
             '--access-basis', 'public_without_login'],
        ]
        for args in commands:
            with self.subTest(command=args[0]):
                cli, python = self.call(args), self.direct(args)
                self.assertEqual(cli.returncode, 0, cli.stderr)
                self.assertEqual(cli.stdout, python.stdout)
                self.assertEqual(cli.stderr, python.stderr)
                json.loads(cli.stdout)
        self.assertFalse((self.work / 'UNEXPECTED').exists())

    def test_relative_files_use_callers_directory(self):
        shutil.copyfile(ROOT / 'examples/posts.json', self.work / 'my posts.json')
        result = self.call(['style', 'my posts.json'])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, self.direct(['style', 'my posts.json']).stdout)

    def test_checkout_and_interpreter_paths_can_contain_spaces(self):
        root = self.fake_checkout()
        executable = self.work / 'python with spaces'
        if os.name == 'nt':
            self.skipTest('Unix interpreter symlink fixture')
        executable.symlink_to(sys.executable)
        result = self.call(['snowflake', '123'], root=root, python=str(executable))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['args'], ['snowflake', '123'])

    def test_offline_children_do_not_receive_api_key(self):
        root = self.fake_checkout()
        env = {**self.env, 'OPENAI_API_KEY': 'synthetic-test-value'}
        for args in (['snowflake', '1'], ['verify'], ['eval', 'prepare', '--output', 'output'],
                     ['review', 'report', '--run', 'run', '--review', 'review.json', '--output', 'report']):
            with self.subTest(command=args):
                result = self.call(args, root=root, env=env)
                self.assertEqual(result.returncode, 0, result.stderr)
                payload = json.loads(result.stdout)
                self.assertFalse(payload['key_present'])
                self.assertEqual((payload['isolated'], payload['no_site']), (1, 1))
                self.assertNotIn('synthetic-test-value', result.stdout + result.stderr)
                if args[0] == 'eval':
                    self.assertIn('--dry-run', payload['args'])

    def test_paid_command_requires_model_and_allow_paid_before_spawning(self):
        root = self.fake_checkout()
        for args in (['--output', 'run'], ['--output', 'run', '--model', 'fixture'],
                     ['--output', 'run', '--allow-paid']):
            result = self.call(['eval', 'run', *args], root=root,
                               env={**self.env, 'OPENAI_API_KEY': 'synthetic-test-value'})
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, '')
            self.assertNotIn('fixture diagnostic', result.stderr)
            self.assertFalse((self.work / 'run').exists())

    def test_explicit_paid_mode_forwards_key_only_to_stub(self):
        root = self.fake_checkout()
        result = self.call(['eval', 'run', '--model', 'fixture', '--output', 'run', '--allow-paid'],
                           root=root, env={**self.env, 'OPENAI_API_KEY': 'synthetic-test-value'})
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload['key_present'])
        self.assertNotIn('--allow-paid', payload['args'])
        self.assertNotIn('--dry-run', payload['args'])
        self.assertEqual(payload['args'][:2], ['--root', str(root.resolve())])
        self.assertNotIn('synthetic-test-value', result.stdout + result.stderr)

    def test_real_runner_with_missing_key_blocks_before_inference(self):
        result = self.call(['eval', 'run', '--model', 'offline-test-model', '--output', 'blocked', '--allow-paid'])
        self.assertEqual(result.returncode, 2)
        manifest = json.loads((self.work / 'blocked/manifest.json').read_text())
        self.assertEqual(manifest['status'], 'blocked_missing_api_key')
        self.assertEqual((manifest['attempted_calls'], manifest['completed_calls']), (0, 0))

    def test_prepare_matches_direct_runner_requests(self):
        args = ['--model', 'offline-fixture', '--cases', '4', '--seed', '13', '--max-output-tokens', '256']
        result = self.call(['eval', 'prepare', '--output', 'rust prepared', *args],
                           env={**self.env, 'OPENAI_API_KEY': 'synthetic-test-value'})
        self.assertEqual(result.returncode, 0, result.stderr)
        script = 'import sys,runpy; sys.path.insert(0,sys.argv.pop(1)); runpy.run_module("receipts.runner",run_name="__main__")'
        direct = subprocess.run([sys.executable, '-I', '-S', '-c', script, str(ROOT / 'src'),
                                 '--root', str(ROOT), '--dry-run', '--output', 'python prepared', *args],
                                cwd=self.work, env=self.env, capture_output=True, text=True, timeout=30)
        self.assertEqual(direct.returncode, 0, direct.stderr)
        for name in ('requests.json', 'cases.json', 'gold.json', 'prompts.json'):
            self.assertEqual((self.work / 'rust prepared' / name).read_bytes(),
                             (self.work / 'python prepared' / name).read_bytes())
        manifest = json.loads((self.work / 'rust prepared/manifest.json').read_text())
        self.assertEqual(manifest['status'], 'dry_run_no_inference')
        self.assertEqual(manifest['planned_calls'], 8)
        self.assertEqual(manifest['attempted_calls'], 0)
        self.assertNotIn('synthetic-test-value', json.dumps(manifest))

    def test_existing_output_is_preserved(self):
        args = ['eval', 'prepare', '--output', 'saved']
        self.assertEqual(self.call(args).returncode, 0)
        before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (self.work / 'saved').iterdir()}
        repeated = self.call(args)
        self.assertEqual(repeated.returncode, 2)
        self.assertIn('choose a fresh', repeated.stderr)
        self.assertNotIn('Traceback', repeated.stderr)
        after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (self.work / 'saved').iterdir()}
        self.assertEqual(before, after)

    def test_opt_in_v02_matches_direct_python_and_keeps_paid_guard(self):
        args = ['--suite', 'v0.2', '--model', 'offline-fixture', '--cases', '4', '--seed', '13']
        result = self.call(['eval', 'prepare', '--output', 'rust-v02', *args],
                           env={**self.env, 'OPENAI_API_KEY': 'synthetic-test-value'})
        self.assertEqual(result.returncode, 0, result.stderr)
        script = 'import sys,runpy; sys.path.insert(0,sys.argv.pop(1)); runpy.run_module("receipts.runner",run_name="__main__")'
        direct = subprocess.run([sys.executable, '-I', '-S', '-c', script, str(ROOT / 'src'),
                                 '--root', str(ROOT), '--dry-run', '--output', 'python-v02', *args],
                                cwd=self.work, env=self.env, capture_output=True, text=True, timeout=30)
        self.assertEqual(direct.returncode, 0, direct.stderr)
        for name in ('requests.json', 'cases.json', 'gold.json', 'prompts.json', 'suite.json'):
            self.assertEqual((self.work / 'rust-v02' / name).read_bytes(),
                             (self.work / 'python-v02' / name).read_bytes())
        manifest = json.loads((self.work / 'rust-v02/manifest.json').read_text())
        self.assertEqual(manifest['suite_version'], 'v0.2')
        self.assertEqual((manifest['planned_calls'], manifest['attempted_calls']), (8, 0))
        blocked = self.call(['eval', 'run', '--suite', 'v0.2', '--output', 'no-paid', '--model', 'fixture'])
        self.assertEqual(blocked.returncode, 2)
        self.assertFalse((self.work / 'no-paid').exists())

    def test_backend_failures_are_not_relabelled_as_success(self):
        result = self.call(['snowflake', '1'], root=self.fake_checkout(),
                           env={**self.env, 'RECEIPTS_TEST_EXIT': '9'})
        self.assertEqual(result.returncode, 9)
        self.assertEqual(result.stderr, 'fixture diagnostic\n')
        self.assertEqual(json.loads(result.stdout)['args'], ['snowflake', '1'])

    def test_opt_in_v03_matches_direct_python_requests(self):
        args = ['--suite', 'v0.3', '--model', 'offline-fixture', '--cases', '4', '--seed', '13']
        result = self.call(['eval', 'prepare', '--output', 'rust-v03', *args],
                           env={**self.env, 'OPENAI_API_KEY': 'synthetic-test-value'})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('No model calls', result.stdout)
        script = 'import sys,runpy; sys.path.insert(0,sys.argv.pop(1)); runpy.run_module("receipts.runner",run_name="__main__")'
        direct = subprocess.run([sys.executable, '-I', '-S', '-c', script, str(ROOT / 'src'),
                                 '--root', str(ROOT), '--dry-run', '--output', 'python-v03', *args],
                                cwd=self.work, env=self.env, capture_output=True, text=True, timeout=30)
        self.assertEqual(direct.returncode, 0, direct.stderr)
        for name in ('requests.json', 'cases.json', 'gold.json', 'prompts.json', 'suite.json'):
            self.assertEqual((self.work / 'rust-v03' / name).read_bytes(),
                             (self.work / 'python-v03' / name).read_bytes())
        manifest = json.loads((self.work / 'rust-v03/manifest.json').read_text())
        self.assertEqual((manifest['suite_version'], manifest['scoring_version']), ('v0.3', 'v0.2'))
        self.assertEqual((manifest['planned_calls'], manifest['attempted_calls']), (8, 0))
        self.assertFalse((self.work / 'rust-v03/action-review-template.json').exists())

    def test_review_forwards_literal_paths_and_optional_digest(self):
        args = ['report', '--run', 'run;$(touch UNEXPECTED)', '--review', 'review file.json',
                '--output', 'report dir', '--expected-run-sha256', 'a' * 64]
        result = self.call(['review', *args], root=self.fake_checkout())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['args'], args)
        self.assertFalse((self.work / 'UNEXPECTED').exists())

    def test_invalid_review_flags_never_reach_python(self):
        root = self.fake_checkout()
        valid = ['review', 'report', '--run', 'run', '--review', 'review', '--output', 'out']
        for args in (valid[:-2], [*valid, '--allow-paid'], [*valid, '--run', 'second'],
                     [*valid, '--expected-run-sha256', 'not-a-digest']):
            result = self.call(args, root=root)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, '')
            self.assertNotIn('fixture diagnostic', result.stderr)

    def test_experiment_operations_strip_key_and_preserve_literal_arguments(self):
        root = self.fake_checkout()
        commands = [
            ['prepare', '--model', 'stub', '--repeats', '2', '--notes', 'notes;$(touch UNEXPECTED).md', '--output', 'plan dir'],
            ['report', '--plan', 'plan dir/plan.json', '--runs', 'index file.json', '--expected-plan-sha256', 'a' * 64, '--output', 'report dir']]
        for args in commands:
            result = self.call(['experiment', *args], root=root, env={**self.env, 'OPENAI_API_KEY': 'synthetic-test-value'})
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertFalse(payload['key_present'])
            expected = [*args, '--root', str(root)] if args[0] == 'prepare' else args
            self.assertEqual(payload['args'], expected)
        self.assertFalse((self.work / 'UNEXPECTED').exists())

    def test_experiment_unknown_duplicate_and_paid_flags_do_not_reach_backend(self):
        root = self.fake_checkout()
        args = ['experiment', 'prepare', '--model', 'stub', '--repeats', '2', '--notes', 'notes', '--output', 'plan']
        for suffix in (['--allow-paid'], ['--model', 'other'], ['--root', 'other'], ['--max-output-tokens', '2049']):
            result = self.call([*args, *suffix], root=root)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, '')
            self.assertNotIn('fixture diagnostic', result.stderr)
        self.assertEqual(self.call(['experiment', 'run'], root=root).returncode, 2)

    def test_real_experiment_prepare_and_pending_report_need_no_inference(self):
        notes = self.work / 'notes.md'
        notes.write_text('Synthetic design notes; no spending or independent review.')
        result = self.call(['experiment', 'prepare', '--model', 'offline-stub', '--repeats', '2', '--notes', 'notes.md', '--output', 'frozen plan'],
                           env={**self.env, 'OPENAI_API_KEY': 'synthetic-test-value'})
        self.assertEqual(result.returncode, 0, result.stderr)
        plan = json.loads((self.work / 'frozen plan/plan.json').read_text())
        self.assertEqual(plan['planned_calls'], 64)
        digest = (self.work / 'frozen plan/plan-sha256.txt').read_text().strip()
        result = self.call(['experiment', 'report', '--plan', 'frozen plan/plan.json', '--runs', 'frozen plan/run-index-template.json',
                            '--expected-plan-sha256', digest, '--output', 'pending report'])
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads((self.work / 'pending report/report.json').read_text())
        self.assertEqual(report['status'], 'incomplete_coverage')
        self.assertIsNone(report['metrics']['paired']['mean_difference_all_planned_pairs'])
        sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tests')]
        try:
            from test_experiment import make_run
            make_run(self.work / 'synthetic-run', plan['slots'][0], model='offline-stub')
        finally:
            del sys.path[:2]
        index = json.loads((self.work / 'frozen plan/run-index-template.json').read_text())
        index['rows'][0].update(run_directory='synthetic-run', unavailable_reason=None, notes='Synthetic local fixture; no provider call.')
        (self.work / 'index.json').write_text(json.dumps(index))
        result = self.call(['experiment', 'report', '--plan', 'frozen plan/plan.json', '--runs', 'index.json',
                            '--expected-plan-sha256', digest, '--output', 'partial comparison'])
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads((self.work / 'partial comparison/report.json').read_text())
        self.assertEqual(report['metrics']['paired']['observed_pairs'], 16)
        self.assertIsNone(report['metrics']['paired']['mean_difference_all_planned_pairs'])

    def test_v04_prepare_and_missing_key_run_keep_new_suite_offline(self):
        result = self.call(['eval', 'prepare', '--suite', 'v0.4', '--output', 'prepared-v04'])
        self.assertEqual(result.returncode, 0, result.stderr)
        manifest = json.loads((self.work / 'prepared-v04/manifest.json').read_text())
        self.assertEqual((manifest['suite_version'], manifest['scoring_version']), ('v0.4', 'v0.2'))
        self.assertEqual((manifest['planned_calls'], manifest['attempted_calls']), (32, 0))
        self.assertEqual(len(manifest['engine_sha256']), 64)
        result = self.call(['eval', 'run', '--suite', 'v0.4', '--model', 'offline-stub', '--output', 'blocked-v04', '--allow-paid'])
        self.assertEqual(result.returncode, 2)
        blocked = json.loads((self.work / 'blocked-v04/manifest.json').read_text())
        self.assertEqual(blocked['status'], 'blocked_missing_api_key')
        self.assertEqual(blocked['attempted_calls'], 0)

    def test_review_runs_real_backend_and_preserves_run_bytes(self):
        # Import only local test helpers; responses and reviewer names are synthetic.
        sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tests')]
        try:
            from test_action_review import make_run
            make_run(self.work / 'review run')
        finally:
            del sys.path[:2]
        run = self.work / 'review run'
        before = {p.name: p.read_bytes() for p in run.iterdir()}
        digest = json.loads((run / 'run-receipt.json').read_text())['run_sha256']
        args = ['review', 'report', '--run', 'review run', '--review', 'review run/action-review-template.json',
                '--output', 'review report', '--expected-run-sha256', digest]
        result = self.call(args, env={**self.env, 'OPENAI_API_KEY': 'synthetic-test-value'})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('No inference', result.stdout)
        data = json.loads((self.work / 'review report/report.json').read_text())
        self.assertEqual(data['trust']['supplied_digest_comparison'], 'matched')
        self.assertTrue(all(v['proposals_with_any_dimension_reviewed'] == 0 for v in data['action_assessments'].values()))
        self.assertEqual(before, {p.name: p.read_bytes() for p in run.iterdir()})
        self.assertEqual(self.call(args).returncode, 2)

    @unittest.skipUnless(os.name == 'posix', 'Unix signal status')
    def test_backend_signal_remains_an_os_signal(self):
        result = self.call(['snowflake', '1'], root=self.fake_checkout(),
                           env={**self.env, 'RECEIPTS_TEST_SIGNAL': 'yes'})
        self.assertEqual(result.returncode, -signal.SIGTERM)

    def waiting_paid_stub(self):
        root = self.fake_checkout()
        (root / 'src/receipts/runner.py').write_text('''import json, os, time
print(json.dumps({"pid": os.getpid(), "group": os.getpgrp()}), flush=True)
time.sleep(60)
''')
        return [str(BINARY), '--root', str(root), '--python', sys.executable,
                'eval', 'run', '--model', 'local-stub', '--output', 'unused', '--allow-paid']

    @staticmethod
    def stop_test_group(group):
        # Isolated test groups also clean up a child left by the old launcher.
        try:
            os.killpg(group, signal.SIGKILL)
        except ProcessLookupError:
            pass

    @unittest.skipUnless(os.name == 'posix', 'Unix process replacement')
    def test_killing_only_cli_pid_stops_paid_backend(self):
        import selectors
        command = self.waiting_paid_stub()
        for sig in (signal.SIGTERM, signal.SIGKILL):
            with self.subTest(signal=sig):
                with subprocess.Popen(command, cwd=self.work, env=self.env,
                                      stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE, text=True,
                                      start_new_session=True) as process:
                    try:
                        with selectors.DefaultSelector() as ready:
                            ready.register(process.stdout, selectors.EVENT_READ)
                            self.assertTrue(ready.select(timeout=5), 'stub did not start')
                        payload = json.loads(process.stdout.readline())
                        process.send_signal(sig)  # Only this PID, not the process group.
                        self.assertEqual(process.wait(timeout=5), -sig)
                        with self.assertRaises(ProcessLookupError):
                            os.kill(payload['pid'], 0)
                        self.assertEqual(payload['pid'], process.pid)
                    finally:
                        self.stop_test_group(process.pid)
                        process.communicate(timeout=5)

    @unittest.skipUnless(os.name == 'posix', 'Unix caller timeout')
    def test_subprocess_run_timeout_leaves_no_paid_backend(self):
        command = self.waiting_paid_stub()
        payload = None
        try:
            with self.assertRaises(subprocess.TimeoutExpired) as caught:
                subprocess.run(command, cwd=self.work, env=self.env,
                               stdin=subprocess.DEVNULL, capture_output=True,
                               timeout=2, start_new_session=True)
            payload = json.loads(caught.exception.stdout)
            with self.assertRaises(ProcessLookupError):
                os.kill(payload['pid'], 0)
            self.assertEqual(payload['pid'], payload['group'])
        finally:
            if payload is not None:
                self.stop_test_group(payload['group'])

    def test_pythonpath_and_cwd_cannot_shadow_backend_or_site(self):
        (self.work / 'receipts.py').write_text('raise RuntimeError("SHADOWED")')
        (self.work / 'sitecustomize.py').write_text('raise RuntimeError("SITE CUSTOMIZED")')
        result = self.call(['snowflake', '1273816504776982529'], env={**self.env, 'PYTHONPATH': str(self.work)})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['authenticated'], False)
        self.assertNotIn('SHADOWED', result.stderr)
        self.assertNotIn('SITE CUSTOMIZED', result.stderr)

    def test_verification_uses_selected_checkout(self):
        result = self.call(['verify'])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('40 preserved files', result.stdout)
        self.assertIn('128 responses', result.stdout)

    def test_help_needs_neither_root_nor_python(self):
        for args in (['--help'], ['--version'], ['receipt', '--help'], ['eval', 'run', '--help'], ['review', 'report', '--help'],
                     ['experiment', '--help'], ['experiment', 'prepare', '--help'], ['experiment', 'report', '--help']):
            result = self.call(args, root=self.work / 'missing', python='missing-python-executable')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(result.stdout)

    def test_missing_python_and_checkout_have_clear_failures(self):
        result = self.call(['verify'], python='missing-python-executable')
        self.assertEqual(result.returncode, 2)
        self.assertIn('--python', result.stderr)
        result = self.call(['verify'], root=self.work)
        self.assertEqual(result.returncode, 2)
        self.assertIn('Python backend', result.stderr)

    def test_naive_timestamp_stays_a_python_validation_failure(self):
        cli = self.call(['utc', '2026-09-01T00:30:00'])
        python = self.direct(['utc', '2026-09-01T00:30:00'])
        self.assertEqual(cli.returncode, python.returncode)
        self.assertNotEqual(cli.returncode, 0)
        self.assertEqual(cli.stdout, '')

    def test_unknown_or_duplicate_eval_flags_cannot_reach_backend(self):
        root = self.fake_checkout()
        for options in (['--allow-paid'], ['--endpoint', 'https://example.invalid'],
                        ['--suite', '../v0.1'], ['--suite', 'v0.1', '--suite', 'v0.2'],
                        ['--cases', '17'], ['--model', 'one', '--model', 'two'],
                        ['--max-output-tokens', '2049']):
            result = self.call(['eval', 'prepare', '--output', 'output', *options], root=root)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, '')
            self.assertFalse((self.work / 'output').exists())


if __name__ == '__main__':
    unittest.main()
