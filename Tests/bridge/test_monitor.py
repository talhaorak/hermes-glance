import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]


class MonitorTests(unittest.TestCase):
    def load(self):
        path = ROOT / 'bridge' / 'monitor.py'
        self.assertTrue(path.exists(), 'read-only monitor is not implemented')
        spec = importlib.util.spec_from_file_location('monitor', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_authenticated_websocket_reads_only_and_handles_ping(self):
        m = self.load()
        self.assertTrue(hasattr(m, 'Runtime'), 'authenticated runtime reader is missing')
        import base64, hashlib, http.server, json, struct, threading
        calls = []
        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def do_GET(self):
                if self.path == '/':
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(b'<script>window.__HERMES_SESSION_TOKEN__ = "test-secret"</script>')
                    return
                self.assert_auth = self.path == '/api/ws?token=test-secret'
                if not self.assert_auth:
                    self.send_error(403)
                    return
                key = self.headers['Sec-WebSocket-Key']
                accept = base64.b64encode(hashlib.sha1((key + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode()).digest()).decode()
                self.send_response(101)
                self.send_header('Upgrade', 'websocket')
                self.send_header('Connection', 'Upgrade')
                self.send_header('Sec-WebSocket-Accept', accept)
                self.end_headers()
                while True:
                    header = self.rfile.read(2)
                    if len(header) != 2:
                        return
                    size = header[1] & 127
                    if size == 126:
                        size = struct.unpack('!H', self.rfile.read(2))[0]
                    mask = self.rfile.read(4)
                    data = self.rfile.read(size)
                    data = bytes(c ^ mask[i % 4] for i, c in enumerate(data))
                    if header[0] & 15 == 8:
                        return
                    req = json.loads(data)
                    calls.append(req['method'])
                    result = {'sessions': [{'id': 'runtime', 'session_key': 'durable', 'status': 'working'}]}
                    payload = json.dumps({'jsonrpc': '2.0', 'id': req['id'], 'result': result}).encode()
                    self.wfile.write(b'\x81\x7e' + struct.pack('!H', len(payload)) + payload)
                    self.wfile.flush()
        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with m.Runtime('http://127.0.0.1:' + str(server.server_port)) as runtime:
                rows = runtime.rpc('session.active_list', {})['sessions']
                self.assertEqual(rows[0]['status'], 'working')
                with self.assertRaises(ValueError):
                    runtime.rpc('session.activate', {'session_id': 'runtime'})
            self.assertEqual(calls, ['session.active_list'])
        finally:
            server.shutdown()
            server.server_close()

    def test_sqlite_fallback_is_unknown_read_only_and_missing_store_not_created(self):
        m = self.load()
        self.assertTrue(hasattr(m, 'Store'), 'read-only fallback is missing')
        import sqlite3, tempfile
        with tempfile.TemporaryDirectory() as directory:
            home = pathlib.Path(directory)
            with m.Store(home) as store:
                self.assertEqual(store.recent(), [])
            self.assertFalse((home / 'state.db').exists())
            db = sqlite3.connect(home / 'state.db')
            db.executescript('CREATE TABLE sessions(id TEXT, title TEXT, source TEXT, started_at REAL, ended_at REAL, last_activity_at REAL, hidden INTEGER, archived INTEGER, profile_name TEXT); CREATE TABLE messages(id INTEGER, session_id TEXT, role TEXT, content TEXT, timestamp REAL);')
            db.execute('INSERT INTO sessions VALUES(?,?,?,?,?,?,?,?,?)', ('real-id', 'Stored', 'desktop', 1, None, 2, 0, 0, 'default'))
            db.execute('INSERT INTO messages VALUES(?,?,?,?,?)', (1, 'real-id', 'assistant', 'Saved answer', 2))
            db.commit()
            db.close()
            with m.Store(home) as store:
                rows = store.recent()
                self.assertEqual(rows[0]['status'], 'unknown')
                self.assertIsNone(rows[0]['waitingReason'])
                self.assertEqual(rows[0]['lines'], ['assistant: Saved answer'])
                with self.assertRaises(sqlite3.OperationalError):
                    store.db.execute('DELETE FROM sessions')

    def test_discovery_requests_numeric_loopback_listener_names(self):
        m = self.load()
        from unittest.mock import patch
        import subprocess
        calls = []
        def run(command, **kwargs):
            calls.append(command)
            if command[0] == '/bin/ps':
                return subprocess.CompletedProcess(command, 0, '42 /venv/python -m hermes_cli.main --profile default serve --host 127.0.0.1 --port 0\n')
            value = 'n127.0.0.1:49354\n' if '-nP' in command else 'nlocalhost:49354\n'
            return subprocess.CompletedProcess(command, 0, value)
        with patch('subprocess.run', side_effect=run):
            self.assertEqual(m.discover_urls(), ['http://127.0.0.1:49354'])
        self.assertIn('-nP', calls[1])

    def test_snapshot_maps_running_and_live_approval_without_claiming_other_profiles(self):
        m = self.load()
        from unittest.mock import patch
        import sqlite3, tempfile
        with tempfile.TemporaryDirectory() as directory:
            db = sqlite3.connect(pathlib.Path(directory) / 'state.db')
            db.executescript('CREATE TABLE sessions(id TEXT, title TEXT, profile_name TEXT); CREATE TABLE messages(id INTEGER, session_id TEXT, role TEXT, content TEXT);')
            db.executemany('INSERT INTO sessions VALUES(?,?,?)', [('stored', 'Session', 'default'), ('foreign', 'Foreign', 'other')])
            db.commit()
            db.close()
            class Reader:
                def rpc(self, method, params):
                    if method == 'session.active_list':
                        return {'sessions': [{'id': 'runtime', 'session_key': 'stored', 'status': 'working'},
                                             {'id': 'runtime-other', 'session_key': 'foreign', 'status': 'working'}]}
                    return {'latest_seq': 4, 'open_requests': [{'method': 'approval', 'params': {'title': 'Permission required'}}]}
                def __exit__(self):
                    pass
            monitor = m.Monitor(directory)
            monitor.runtime = Reader()
            result = monitor.snapshot()
            self.assertTrue(result['connected'])
            self.assertEqual(len(result['sessions']), 1)
            self.assertEqual(result['sessions'][0]['status'], 'waiting')
            self.assertEqual(result['sessions'][0]['waitingReason'], 'approval: Permission required')
            self.assertEqual(monitor.cursors, {'runtime': 4})
            self.assertIn('ownership', result['error'])

    def test_discovery_timeout_returns_json_instead_of_crashing(self):
        m = self.load()
        from unittest.mock import patch
        import subprocess, tempfile
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(m, 'discover_urls', side_effect=subprocess.TimeoutExpired('ps', 3)):
                result = m.Monitor(directory).snapshot()
            self.assertFalse(result['connected'])
            self.assertEqual(result['sessions'], [])

    def test_once_cli_emits_honest_disconnected_json(self):
        m = self.load()
        self.assertTrue(hasattr(m, 'main'), 'JSON process CLI is missing')
        import json, subprocess, sys, tempfile
        with tempfile.TemporaryDirectory() as directory:
            run = subprocess.run([sys.executable, str(ROOT / 'bridge/monitor.py'), '--once',
                                  '--home', directory, '--url', 'http://127.0.0.1:1'],
                                 text=True, capture_output=True, timeout=10)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(run.stderr, '')
            payload = json.loads(run.stdout)
            self.assertEqual(set(payload), {'connected', 'updatedAt', 'error', 'sessions'})
            self.assertFalse(payload['connected'])
            self.assertEqual(payload['sessions'], [])
            self.assertIn('unavailable', payload['error'])
            self.assertNotIn('Traceback', run.stdout)

    def test_transcript_decodes_blocks_and_ignores_rewound_messages(self):
        m = self.load()
        messages = [{'role': 'assistant', 'content': '[{"type":"text","text":"Visible"},{"type":"image","url":"not text"}]'},
                    {'role': 'assistant', 'content': 'Rewound', 'active': 0},
                    {'role': 'tool', 'content': 'Not a transcript line'},
                    {'role': 'user', 'content': 'Hidden', 'display_kind': 'hidden'}]
        self.assertEqual(m.transcript_lines(messages), ['assistant: Visible'])

    def test_internal_envelopes_do_not_replace_visible_transcript_or_summary(self):
        m = self.load()
        prefixes = [
            '[ASYNC DELEGATION BATCH COMPLETE — results follow]',
            '[Skills pruned during compression — reload before acting on them]',
            'The task list above was carried across the compression boundary verbatim.',
        ]
        genuine = [
            {'role': 'user', 'content': '[Please keep bracketed user requests]'},
            {'role': 'assistant', 'content': [{'type': 'text', 'text': 'Checking now.'}]},
            {'role': 'assistant', 'content': 'Verified answer.'},
        ]
        internal = [{'role': 'user', 'content': prefix + '\nInternal details'} for prefix in prefixes]
        internal += [
            {'role': 'user', 'content': 'Worker results', 'display_kind': 'async_delegation_complete'},
            {'role': 'user', 'content': 'Compressed history', '_compressed_summary': 1},
        ]
        expected = ['user: [Please keep bracketed user requests]',
                    'assistant: Checking now.', 'assistant: Verified answer.']
        self.assertEqual(m.transcript_lines(genuine + internal), expected)
        for preview in prefixes:
            with self.subTest(preview=preview):
                item = m.live_item({'session_key': 'stored', 'preview': '  ' + preview},
                                   {}, genuine + internal, 'default')
                self.assertEqual(item['summary'], expected[-1])
                empty = m.live_item({'session_key': 'stored', 'preview': preview},
                                    {}, internal, 'default')
                self.assertEqual(empty['summary'], '')
        item = m.live_item({'session_key': 'stored', 'preview': '[Real preview]'},
                           {}, genuine, 'default')
        self.assertEqual(item['summary'], 'assistant: Verified answer.')

    def test_live_status_uses_explicit_requests_and_durable_deeplink(self):
        m = self.load()
        item = m.live_item({'id': 'runtime-1', 'session_key': 'stored-1',
                            'status': 'idle', 'title': 'Real title', 'last_active': 1},
                           {'open_requests': [{'method': 'clarify', 'params': {'question': 'Choose?'}}]},
                           [{'role': 'user', 'content': 'one\ntwo\nthree\nfour\nfive'}], 'default')
        self.assertEqual(item['id'], 'stored-1')
        self.assertEqual(item['status'], 'waiting')
        self.assertEqual(item['openURL'], 'hermes://open/stored-1')
        self.assertEqual(item['waitingReason'], 'clarify: Choose?')
        self.assertEqual(item['lines'], ['user: two', 'user: three', 'user: four', 'user: five'])
        idle = m.live_item({'id': 'runtime-1', 'session_key': 'stored-1', 'status': 'idle'}, {}, [], 'default')
        self.assertEqual(idle['status'], 'idle')
        self.assertIsNone(idle['waitingReason'])


if __name__ == '__main__':
    unittest.main()
