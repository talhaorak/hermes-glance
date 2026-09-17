#!/usr/bin/env python3
"""Read-only Hermes Glance monitor. Python standard library only."""
import datetime
import json
from urllib.parse import quote, urlsplit
import base64
import hashlib
import http.client
import os
import re
import socket
import struct
import time
import subprocess
import sqlite3
from pathlib import Path


class Store:
    """No Hermes imports: its SessionDB constructor can migrate/write the DB."""
    def __init__(self, home, profile='default'):
        self.path = Path(home) / 'state.db'
        self.profile = profile
        self.db = None

    def __enter__(self):
        if self.path.is_file():
            self.db = sqlite3.connect(self.path.resolve().as_uri() + '?mode=ro', uri=True, timeout=1)
            self.db.row_factory = sqlite3.Row
            self.db.execute('PRAGMA query_only=ON')
        return self

    def __exit__(self, *args):
        if self.db:
            self.db.close()

    def messages(self, durable):
        if not self.db:
            return []
        return list(reversed([dict(row) for row in self.db.execute(
            "SELECT * FROM messages WHERE session_id=? AND role IN ('user','assistant') ORDER BY id DESC LIMIT 12", (durable,))]))

    def row(self, durable):
        if not self.db:
            return None
        row = self.db.execute('SELECT id,title,profile_name FROM sessions WHERE id=?', (durable,)).fetchone()
        return dict(row) if row else None

    def recent(self, limit=20):
        if not self.db:
            return []
        rows = self.db.execute("SELECT id,title,started_at,last_activity_at,ended_at FROM sessions WHERE COALESCE(hidden,0)=0 AND COALESCE(archived,0)=0 AND source NOT IN ('tool','kanban') AND (profile_name IS NULL OR profile_name=?) ORDER BY COALESCE(last_activity_at,started_at) DESC LIMIT ?", (self.profile, limit))
        result = []
        for record in rows:
            row = dict(record)
            row.update(session_key=row['id'], status='unknown', last_active=row['last_activity_at'])
            # ended_at means a session was closed, not that its task succeeded.
            result.append(live_item(row, {}, self.messages(row['id']), self.profile))
        return result



class Runtime:
    """Small RFC6455 read client; never attaches/rebinds/creates a session.

    The only requests allowed are observational RPCs. Credentials remain in
    memory, never command arguments or output. Hermes requires the local WS
    token in its upgrade query (HTTP auth headers are not supported there).
    """
    ALLOWED = frozenset(('session.active_list', 'session.events.since', 'session.history'))

    def __init__(self, url):
        parsed = urlsplit(url)
        if (parsed.scheme != 'http' or parsed.hostname not in ('127.0.0.1', '::1', 'localhost')
                or parsed.username or parsed.password or parsed.path not in ('', '/') or parsed.query or parsed.fragment):
            raise ValueError('Only a loopback HTTP Hermes runtime is allowed')
        self.host, self.port = parsed.hostname, parsed.port or 80
        self.sock = self.stream = None
        self.sequence = 0

    def __enter__(self):
        conn = http.client.HTTPConnection(self.host, self.port, timeout=3)
        try:
            conn.request('GET', '/')
            response = conn.getresponse()
            if response.status != 200:
                raise OSError('Runtime index unavailable')
            html = response.read(2 * 1024 * 1024).decode('utf-8', errors='replace')
        finally:
            conn.close()
        match = re.search(r'window\.__HERMES_SESSION_TOKEN__\s*=\s*("(?:\\.|[^"\\])*")', html)
        if not match:
            raise OSError('Local runtime authentication unavailable')
        token = json.loads(match[1])
        if not isinstance(token, str) or '\r' in token or '\n' in token:
            raise OSError('Invalid local credential')
        key = base64.b64encode(os.urandom(16)).decode()
        self.sock = socket.create_connection((self.host, self.port), timeout=5)
        self.stream = self.sock.makefile('rb')
        host = '[' + self.host + ']' if ':' in self.host else self.host
        request = (f'GET /api/ws?token={quote(token, safe="")} HTTP/1.1\r\nHost: {host}:{self.port}\r\n'
                   'Upgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Version: 13\r\n'
                   f'Sec-WebSocket-Key: {key}\r\nX-Hermes-Session-Token: {token}\r\n\r\n')
        try:
            self.sock.sendall(request.encode())
            status = self.stream.readline(8192)
            headers = {}
            for _ in range(100):
                line = self.stream.readline(8192)
                if line in (b'\r\n', b'\n', b''):
                    break
                name, value = line.decode().split(':', 1)
                headers[name.lower()] = value.strip()
            accept = base64.b64encode(hashlib.sha1((key + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode()).digest()).decode()
            if b' 101 ' not in status or headers.get('sec-websocket-accept') != accept:
                raise OSError('Runtime WebSocket authentication failed')
            return self
        except Exception:
            self.__exit__(None, None, None)
            raise

    def __exit__(self, *args):
        if self.stream:
            self.stream.close()
        if self.sock:
            self.sock.close()

    def send(self, payload, opcode=1):
        mask = os.urandom(4)
        size = len(payload)
        length = bytes([0x80 | size]) if size < 126 else (b'\xfe' + struct.pack('!H', size) if size < 65536 else b'\xff' + struct.pack('!Q', size))
        self.sock.sendall(bytes([0x80 | opcode]) + length + mask + bytes(c ^ mask[i % 4] for i, c in enumerate(payload)))

    def exact(self, size):
        data = self.stream.read(size)
        if len(data) != size:
            raise OSError('Runtime disconnected')
        return data

    def receive(self):
        parts = []
        while True:
            first, second = self.exact(2)
            opcode, size = first & 15, second & 127
            if size == 126:
                size = struct.unpack('!H', self.exact(2))[0]
            elif size == 127:
                size = struct.unpack('!Q', self.exact(8))[0]
            if size > 16 * 1024 * 1024:
                raise OSError('Runtime frame too large')
            mask = self.exact(4) if second & 128 else None
            payload = self.exact(size)
            if mask:
                payload = bytes(c ^ mask[i % 4] for i, c in enumerate(payload))
            if opcode == 8:
                raise OSError('Runtime closed connection')
            if opcode == 9:
                self.send(payload, 10)
                continue
            if opcode == 10:
                continue
            if opcode not in (0, 1):
                raise OSError('Unexpected runtime frame')
            parts.append(payload)
            if sum(map(len, parts)) > 16 * 1024 * 1024:
                raise OSError('Runtime message too large')
            if first & 128:
                return b''.join(parts).decode('utf-8')

    def rpc(self, method, params):
        if method not in self.ALLOWED:
            raise ValueError('Only read-only runtime methods are allowed')
        self.sequence += 1
        request_id = self.sequence
        self.send(json.dumps({'jsonrpc': '2.0', 'id': request_id, 'method': method, 'params': params}).encode())
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            for line in self.receive().splitlines():
                response = json.loads(line)
                if response.get('id') == request_id and ('result' in response or 'error' in response):
                    if 'error' in response:
                        raise OSError('Runtime read RPC failed')
                    return response['result']
        raise TimeoutError('Runtime read timed out')


def iso(value=None):
    if isinstance(value, str):
        try:
            return datetime.datetime.fromisoformat(value.replace('Z', '+00:00')).isoformat()
        except ValueError:
            pass
    return datetime.datetime.fromtimestamp(value or 0, datetime.timezone.utc).isoformat()


def internal_envelope(content):
    # Match known runtime envelopes only, not arbitrary bracketed user text.
    return content.lstrip().startswith((
        '[ASYNC DELEGATION BATCH COMPLETE',
        '[Skills pruned during compression',
        'The task list above was carried across the compression boundary verbatim',
    ))


def transcript_lines(messages):
    lines = []
    for message in messages:
        if (message.get('role') not in ('user', 'assistant')
                or message.get('display_kind') in ('hidden', 'async_delegation_complete')
                or message.get('_compressed_summary') == 1 or message.get('active', 1) == 0):
            continue
        content = message.get('display_content') or message.get('content', message.get('text', ''))
        if isinstance(content, str) and content.lstrip().startswith('['):
            try:
                decoded = json.loads(content)
                if isinstance(decoded, list):
                    content = decoded
            except ValueError:
                pass
        if isinstance(content, list):
            content = '\n'.join(str(part.get('text', '')) for part in content if isinstance(part, dict) and part.get('type', 'text') == 'text')
        if isinstance(content, str) and not internal_envelope(content):
            lines.extend(f"{message['role']}: {line.strip()[:500]}" for line in content.splitlines() if line.strip())
    return lines[-4:]


def live_item(row, replay, messages, profile):
    # Never confuse the ephemeral runtime id with the durable desktop route.
    durable = row['session_key']
    human_methods = {'approval', 'clarify', 'sudo', 'secret', 'vault.unlock_prompt',
                     'vault.save_login', 'vault.code'}
    requests = [r for r in replay.get('open_requests', []) or []
                if r.get('method') in human_methods]
    reason = None
    if requests:
        request = requests[0]
        params = request.get('params') or {}
        reason = str(request.get('method') or 'Input requested')
        detail = params.get('question') or params.get('message') or params.get('title')
        if detail:
            reason += ': ' + str(detail)[:240]
    status = {'working': 'running', 'starting': 'running', 'running': 'running',
              'idle': 'idle', 'waiting': 'unknown', 'completed': 'completed'}.get(row.get('status'), 'unknown')
    if requests:
        status = 'waiting'
    lines = transcript_lines(messages)
    # active_list.preview may be the initial user prompt, not latest output.
    assistant = transcript_lines([msg for msg in messages if msg.get('role') == 'assistant'])
    preview = assistant[-1] if assistant else ''
    return {'id': durable, 'title': row.get('title') or durable, 'profile': profile,
            'status': status, 'summary': preview[:300],
            'lines': lines, 'updatedAt': iso(row.get('last_active') or row.get('started_at')),
            'openURL': 'hermes://open/' + quote(durable, safe=''), 'waitingReason': reason,
            'live': False}


def discover_urls(profile='default'):
    """Inspect only Hermes serve/dashboard listeners; no port sweep or env read."""
    import shlex
    import subprocess
    result = subprocess.run(['/bin/ps', '-axo', 'pid=,args='], capture_output=True, text=True, timeout=3)
    urls = []
    for line in result.stdout.splitlines():
        try:
            pid, command = line.strip().split(None, 1)
            args = shlex.split(command)
        except ValueError:
            continue
        if not any(args[i:i + 2] == ['-m', 'hermes_cli.main'] for i in range(len(args))):
            continue
        if not any(word in args for word in ('serve', 'dashboard')):
            continue
        selected = 'default'
        for flag in ('--profile', '-p'):
            if flag in args and args.index(flag) + 1 < len(args):
                selected = args[args.index(flag) + 1]
        if selected != profile:
            continue
        ports = subprocess.run(['/usr/sbin/lsof', '-nP', '-a', '-p', pid, '-iTCP', '-sTCP:LISTEN', '-Fn'],
                               capture_output=True, text=True, timeout=3)
        for entry in ports.stdout.splitlines():
            match = re.fullmatch(r'n127\.0\.0\.1:(\d+)', entry)
            if match:
                urls.append('http://127.0.0.1:' + match[1])
    return list(dict.fromkeys(urls))


class Activity:
    """Bounded public event projection, never reasoning, args or tool results.

    Replay frames have no timestamp: activityAt is local observation time, not
    the time an older retained event was emitted. One object per runtime id.
    """
    def __init__(self):
        self.seq = 0
        self.lines = []
        self.text = ''
        self.streaming = False
        self.activity_at = None

    def consume(self, sid, replay):
        for event in replay.get('events', []):
            seq = event.get('seq', 0)
            if event.get('session_id') != sid or seq <= self.seq:
                continue
            self.seq = seq
            kind, payload = event.get('type'), event.get('payload') or {}
            line = None
            if kind == 'message.start':
                self.streaming = False
                self.text = ''
            elif kind in ('message.delta', 'message.interim', 'message.complete'):
                text = payload.get('text')
                if not isinstance(text, str) or internal_envelope(text):
                    continue
                if kind == 'message.delta':
                    self.text = ((self.text if self.streaming else '') + text)[-6000:]
                else:
                    self.text = text[-6000:]
                line = 'assistant: ' + ' '.join(self.text.split())[-500:]
                if self.streaming and self.lines:
                    self.lines.pop()
                self.streaming = kind == 'message.delta'
                if not self.text.strip():
                    continue
            elif kind == 'status.update':
                if payload.get('kind') in ('status', 'lifecycle', 'compacting', 'goal', 'loop', 'heartbeat', 'process'):
                    text = payload.get('text')
                    if isinstance(text, str) and not internal_envelope(text):
                        line = ' '.join(text.split())[:500]
                self.streaming = False
                self.text = ''
            elif kind in ('tool.start', 'tool.complete', 'tool.generating'):
                name = payload.get('name', '')
                # Names, not free-form tool preview/arguments/results.
                if isinstance(name, str) and re.fullmatch(r'[\w.:-]{1,100}', name):
                    label = {'tool.start': 'Tool started', 'tool.complete': 'Tool finished',
                             'tool.generating': 'Preparing tool'}[kind]
                    line = label + ': ' + name
                self.streaming = False
                self.text = ''
            if line:
                self.lines.append(line)
                self.lines = self.lines[-12:]
                self.activity_at = iso(time.time())
        self.seq = max(self.seq, replay.get('latest_seq', 0))

    def apply(self, item):
        if self.lines:
            item.update(lines=list(self.lines), summary=self.lines[-1][:300],
                        activity=self.lines[-1], activityAt=self.activity_at,
                        live=item['status'] == 'running')
        return item


class Monitor:
    def __init__(self, home, profile='default', url=None):
        self.home, self.profile, self.url = Path(home), profile, url
        self.runtime = None
        self.cursors = {}
        self.activities = {}
        self.identities = {}
        self.epochs = {}

    def close(self):
        if self.runtime:
            self.runtime.__exit__()
            self.runtime = None
        self.cursors.clear()
        self.activities.clear()
        self.identities.clear()
        self.epochs.clear()

    def snapshot(self):
        stamp = iso(time.time())
        error = None
        try:
            if self.runtime is None:
                for url in ([self.url] if self.url else discover_urls(self.profile)):
                    try:
                        self.runtime = Runtime(url).__enter__()
                        break
                    except (OSError, ValueError, http.client.HTTPException):
                        continue
            if self.runtime is None:
                raise OSError('Runtime unavailable')
            rows = self.runtime.rpc('session.active_list', {})['sessions']
            sessions = []
            observed = set()
            replay_gap = False
            with Store(self.home, self.profile) as store:
                for row in rows:
                    durable, runtime_id = row.get('session_key'), row.get('id')
                    if not durable or not runtime_id:
                        continue
                    stored = store.row(durable)
                    # active_list is process-wide and lacks an owner. Do not
                    # mislabel other profiles or invent identities for new rows.
                    if not stored or stored.get('profile_name') not in (None, '', self.profile):
                        error = 'Some runtime sessions omitted: profile ownership not verified in selected store.'
                        continue
                    observed.add(runtime_id)
                    if self.identities.get(runtime_id) != durable:
                        self.cursors.pop(runtime_id, None)
                        self.activities.pop(runtime_id, None)
                        self.epochs.pop(runtime_id, None)
                    self.identities[runtime_id] = durable
                    last_seen = self.cursors.get(runtime_id, 0)
                    replay = self.runtime.rpc('session.events.since', {
                        'session_id': runtime_id, 'last_seen': last_seen})
                    epoch = replay.get('epoch')
                    if (runtime_id in self.epochs and self.epochs[runtime_id] != epoch
                            or replay.get('latest_seq', 0) < last_seen):
                        self.activities.pop(runtime_id, None)
                        replay = self.runtime.rpc('session.events.since', {
                            'session_id': runtime_id, 'last_seen': 0})
                    self.epochs[runtime_id] = replay.get('epoch')
                    if replay.get('truncated'):
                        self.activities.pop(runtime_id, None)
                        replay_gap = True
                    activity = self.activities.setdefault(runtime_id, Activity())
                    activity.consume(runtime_id, replay)
                    self.cursors[runtime_id] = activity.seq
                    messages = store.messages(durable)
                    sessions.append(activity.apply(live_item(row, replay, messages, self.profile)))
            for cache in (self.cursors, self.activities, self.identities, self.epochs):
                for sid in set(cache) - observed:
                    del cache[sid]
            priority = {'waiting': 0, 'running': 1, 'idle': 2, 'completed': 3, 'unknown': 4}
            sessions.sort(key=lambda item: (priority[item['status']], item['id']))
            coverage = 'Polling runtime events (~1s); selected-profile Desktop runtime only.'
            if replay_gap:
                coverage += ' Event replay gap: retained tail only; older events unavailable.'
            return {'connected': True, 'updatedAt': stamp,
                    'error': coverage + (' ' + error.strip() if error else ''), 'sessions': sessions}
        except (OSError, ValueError, KeyError, TypeError, sqlite3.Error, http.client.HTTPException, subprocess.TimeoutExpired):
            # Never print exception bodies: network errors can contain credentials.
            self.close()
            error = 'Live runtime unavailable; SQLite history only. Running and pending-input state unknown.'
        try:
            with Store(self.home, self.profile) as store:
                sessions = store.recent()
        except (OSError, sqlite3.Error, ValueError):
            sessions = []
            error += ' Session store unavailable or incompatible.'
        return {'connected': False, 'updatedAt': stamp, 'error': error, 'sessions': sessions}


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--once', action='store_true', help='Emit one JSON snapshot and exit')
    parser.add_argument('--home', default=os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
    parser.add_argument('--profile', default=None, help='Selected profile label (inferred from --home)')
    parser.add_argument('--url', default=os.environ.get('HERMES_GLANCE_URL'), help='Explicit loopback runtime URL; otherwise discover')
    options = parser.parse_args()
    home = Path(options.home).expanduser().resolve()
    profile = options.profile or (home.name if home.parent.name == 'profiles' else 'default')
    monitor = Monitor(home, profile, options.url)
    try:
        while True:
            start = time.monotonic()
            print(json.dumps(monitor.snapshot(), ensure_ascii=True, separators=(',', ':')), flush=True)
            if options.once:
                break
            # No read-only session subscription exists in this installed API:
            # session events route to attached transports. Do NOT attach/resume.
            # RPC replay polling is ~1Hz, with a 4Hz hard output ceiling even
            # after slow calls; no extra model calls, threads or busy spin.
            time.sleep(max(0.25, 1 - (time.monotonic() - start)))
    except (KeyboardInterrupt, BrokenPipeError):
        pass
    finally:
        monitor.close()


if __name__ == '__main__':
    main()
