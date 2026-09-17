"""Socket fixtures match event_replay.py params and contracts/events.py.
No agent invocation, attach, resume or ownership-changing RPC is used.
"""
import base64
import hashlib
import http.server
import importlib.util
import json
from pathlib import Path
import sqlite3
import struct
import tempfile
import threading
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('monitor_live', ROOT / 'bridge/monitor.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def event(seq, kind, payload=None, sid='runtime'):
    result = dict(seq=seq, type=kind, session_id=sid)
    if payload is not None:
        result['payload'] = payload
    return result


class LiveEventsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        db = sqlite3.connect(Path(self.temp.name) / 'state.db')
        db.executescript("CREATE TABLE sessions(id TEXT, title TEXT, source TEXT, started_at REAL, ended_at REAL, last_activity_at REAL, hidden INTEGER, archived INTEGER, profile_name TEXT); CREATE TABLE messages(id INTEGER, session_id TEXT, role TEXT, content TEXT);")
        db.execute('INSERT INTO sessions VALUES(?,?,?,?,?,?,?,?,?)', ('durable', 'Session', 'desktop', 1, None, 2, 0, 0, 'default'))
        db.execute('INSERT INTO messages VALUES(?,?,?,?)', (1, 'durable', 'assistant', 'Old persisted answer'))
        db.commit()
        db.close()
        self.calls = []
        self.rows = [dict(id='runtime', session_key='durable', status='working', preview='First prompt')]
        self.replay = dict(events=[], latest_seq=0, epoch='epoch-1', truncated=False, open_requests=[])
        owner = self
        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def frame(self, data, opcode=1):
                self.wfile.write(bytes([128 | opcode, 126]) + struct.pack('!H', len(data)) + data)
                self.wfile.flush()
            def do_GET(self):
                if self.path == '/':
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(b'window.__HERMES_SESSION_TOKEN__ = "fixture-token"')
                    return
                if self.path != '/api/ws?token=fixture-token':
                    self.send_error(403)
                    return
                key = self.headers['Sec-WebSocket-Key']
                accept = base64.b64encode(hashlib.sha1((key + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode()).digest()).decode()
                self.send_response(101)
                self.send_header('Upgrade', 'websocket')
                self.send_header('Connection', 'Upgrade')
                self.send_header('Sec-WebSocket-Accept', accept)
                self.end_headers()
                self.frame(json.dumps({'jsonrpc':'2.0','method':'event','params':{'type':'gateway.ready','session_id':'','payload':{'skin':{},'change_events':True,'replay_epoch':'epoch-1'}}}).encode())
                self.frame(b'ping', 9)
                while True:
                    header = self.rfile.read(2)
                    if len(header) != 2:
                        return
                    size = header[1] & 127
                    if size == 126:
                        size = struct.unpack('!H', self.rfile.read(2))[0]
                    elif size == 127:
                        size = struct.unpack('!Q', self.rfile.read(8))[0]
                    mask = self.rfile.read(4)
                    data = self.rfile.read(size)
                    data = bytes(c ^ mask[i % 4] for i, c in enumerate(data))
                    if header[0] & 15 == 10:
                        continue
                    request = json.loads(data)
                    owner.calls.append(request)
                    result = {'sessions': owner.rows} if request['method'] == 'session.active_list' else owner.replay
                    self.frame(json.dumps(dict(jsonrpc='2.0', id=request['id'], result=result)).encode())
        self.server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.monitor = m.Monitor(self.temp.name, url=f'http://127.0.0.1:{self.server.server_port}')

    def tearDown(self):
        self.monitor.close()
        self.server.shutdown()
        self.server.server_close()
        self.temp.cleanup()

    def test_truncated_warning_is_bounded_across_sessions(self):
        db = sqlite3.connect(Path(self.temp.name) / 'state.db')
        db.execute('INSERT INTO sessions VALUES(?,?,?,?,?,?,?,?,?)', ('durable-2', 'Second', 'desktop', 1, None, 2, 0, 0, 'default'))
        db.commit()
        db.close()
        self.rows.append(dict(id='runtime-2', session_key='durable-2', status='working'))
        self.replay.update(latest_seq=1, truncated=True, events=[event(1, 'message.delta', {'text':'Only first session'})])
        snap = self.monitor.snapshot()
        self.assertEqual(snap['error'].count('Event replay gap'), 1)
        items = {x['id']:x for x in snap['sessions']}
        self.assertEqual(items['durable']['summary'], 'assistant: Only first session')
        self.assertEqual(items['durable-2']['summary'], '')
        self.assertFalse(items['durable-2']['live'])

    def test_segment_boundaries_status_tail_and_socket_disconnect(self):
        import socket
        self.replay.update(latest_seq=5, events=[
            event(1, 'message.interim', {'text':'First segment', 'already_streamed':False}),
            event(2, 'message.delta', {'text':'Final '}),
            event(3, 'message.delta', {'text':'segment'}),
            event(4, 'message.complete', {'text':'Final segment', 'status':'complete', 'reasoning':'PRIVATE'}),
            event(5, 'status.update', {'kind':'compacting','text':'Compacting context'}),
        ])
        item = self.monitor.snapshot()['sessions'][0]
        self.assertEqual(item['lines'], ['assistant: First segment', 'assistant: Final segment', 'Compacting context'])
        self.assertEqual(item['summary'], 'Compacting context')
        self.replay.update(latest_seq=6, events=[event(6, 'message.delta', {'text':'Fresh segment'})])
        self.assertEqual(self.monitor.snapshot()['sessions'][0]['summary'], 'assistant: Fresh segment')
        self.replay.update(latest_seq=25, events=[event(n, 'tool.start', {'name':'read_file', 'tool_id':str(n)}) for n in range(7,26)])
        self.assertEqual(len(self.monitor.snapshot()['sessions'][0]['lines']), 12)
        self.monitor.runtime.sock.shutdown(socket.SHUT_RDWR)
        snap = self.monitor.snapshot()
        self.assertFalse(snap['connected'])
        self.assertFalse(snap['sessions'][0]['live'])
        self.assertEqual(snap['sessions'][0]['status'], 'unknown')
        self.assertEqual(snap['sessions'][0]['summary'], 'assistant: Old persisted answer')
        self.assertEqual(self.monitor.cursors, {})
        self.assertEqual(self.monitor.activities, {})

    def test_continuous_cli_polls_one_second_and_displays_new_events(self):
        import select, subprocess, sys, time
        process = subprocess.Popen([sys.executable, str(ROOT / 'bridge/monitor.py'),
                                    '--home', self.temp.name, '--url', self.monitor.url],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stamps, snapshots = [], []
        try:
            for index in range(3):
                ready, _, _ = select.select([process.stdout], [], [], 2.5)
                self.assertTrue(ready, 'Polling snapshot did not arrive within 2.5s')
                snapshots.append(json.loads(process.stdout.readline()))
                stamps.append(time.monotonic())
                self.replay.update(latest_seq=index + 1, events=[event(index + 1, 'message.interim', {'text':f'Update {index}', 'already_streamed':False})])
            self.assertLess(stamps[-1] - stamps[0], 2.5)
            self.assertGreater(stamps[1] - stamps[0], 0.25)
            self.assertEqual(snapshots[-1]['sessions'][0]['summary'], 'assistant: Update 1')
            self.assertIn('Polling', snapshots[-1]['error'])
        finally:
            process.terminate()
            _, err = process.communicate(timeout=5)
            self.assertEqual(err, '')

    def test_epoch_gap_and_identity_changes_never_reuse_stale_tail(self):
        self.replay.update(latest_seq=100, events=[event(100, 'message.interim', {'text':'Old runtime', 'already_streamed':False})])
        self.monitor.snapshot()
        self.replay.update(epoch='epoch-2', latest_seq=1, events=[event(1, 'message.delta', {'text':'New runtime'})])
        item = self.monitor.snapshot()['sessions'][0]
        self.assertEqual(item['summary'], 'assistant: New runtime')
        self.assertEqual(self.calls[-1]['params']['last_seen'], 0)
        self.replay.update(latest_seq=9, truncated=True, events=[event(9, 'message.delta', {'text':'Retained tail'})])
        snap = self.monitor.snapshot()
        self.assertEqual(snap['sessions'][0]['lines'], ['assistant: Retained tail'])
        self.assertIn('gap', snap['error'])
        self.rows[0]['id'] = 'different-runtime'
        self.replay.update(latest_seq=10, truncated=False, events=[event(10, 'message.delta', {'text':'FOREIGN'}, sid='runtime')])
        item = self.monitor.snapshot()['sessions'][0]
        self.assertEqual(item['summary'], 'assistant: Old persisted answer')
        self.assertNotIn('runtime', self.monitor.cursors)
        self.monitor.close()
        self.assertEqual(self.monitor.activities, {})
        self.assertEqual(self.monitor.cursors, {})

    def test_waiting_requires_human_request_and_latest_assistant_wins(self):
        self.rows[0]['status'] = 'waiting'
        self.replay['open_requests'] = [{'id':'srq-1', 'method':'terminal.read', 'params':{}}]
        item = self.monitor.snapshot()['sessions'][0]
        self.assertEqual(item['status'], 'unknown')
        self.assertIsNone(item['waitingReason'])
        self.assertEqual(item['summary'], 'assistant: Old persisted answer')
        self.replay['open_requests'] = [{'id':'srq-2','method':'approval','params':{'title':'Permission required','command':'PRIVATE'}}]
        self.assertEqual(self.monitor.snapshot()['sessions'][0]['status'], 'waiting')
        self.rows[0]['status'] = 'working'
        self.replay['open_requests'] = []
        item = self.monitor.snapshot()['sessions'][0]
        self.assertEqual(item['status'], 'running')
        self.assertIsNone(item['waitingReason'])
        self.assertFalse(item['live'])
        self.assertEqual(m.transcript_lines([{'role':'assistant','content':[{'type':'thinking','text':'PRIVATE'}, {'type':'text','text':'Public'}]}]), ['assistant: Public'])

    def test_socket_replay_text_tool_activity_dedupe_and_private_fields(self):
        self.replay.update(latest_seq=8, events=[
            event(1, 'message.start'),
            event(2, 'message.delta', {'text':'Checking '}),
            event(3, 'message.delta', {'text':'the bridge.'}),
            event(4, 'message.interim', {'text':'Checking the bridge.', 'already_streamed':True}),
            event(5, 'reasoning.delta', {'text':'PRIVATE reasoning'}),
            event(6, 'thinking.delta', {'text':'PRIVATE thinking'}),
            event(7, 'tool.start', {'tool_id':'t1','name':'terminal','args':{'command':'PRIVATE secret'}}),
            event(8, 'tool.complete', {'tool_id':'t1','name':'terminal','duration_s':0.5,'result':'PRIVATE result','summary':'PRIVATE summary'}),
        ])
        first = self.monitor.snapshot()
        self.assertTrue(first['connected'])
        item = first['sessions'][0]
        self.assertEqual(item['summary'], 'Tool finished: terminal')
        self.assertEqual(item['lines'], ['assistant: Checking the bridge.', 'Tool started: terminal', 'Tool finished: terminal'])
        self.assertTrue(item['live'])
        self.assertEqual(item['activity'], 'Tool finished: terminal')
        self.assertNotIn('PRIVATE', json.dumps(first))
        self.assertEqual(item['openURL'], 'hermes://open/durable')
        again = self.monitor.snapshot()['sessions'][0]
        self.assertEqual(again['lines'], item['lines'])
        self.assertEqual(again['activityAt'], item['activityAt'])
        replays = [r for r in self.calls if r['method'] == 'session.events.since']
        self.assertEqual([r['params']['last_seen'] for r in replays], [0, 8])
        self.assertEqual(set(r['method'] for r in self.calls), {'session.active_list','session.events.since'})
