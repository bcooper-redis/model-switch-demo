"""Launch the local API and its separate durable worker. Ctrl-C stops both."""
import signal
import os
import socket
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
port = int(os.environ.get('DEMO_PORT', '8765'))
with socket.socket() as check:
    check.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        check.bind(('127.0.0.1', port))
    except OSError as exc:
        raise SystemExit(f'Cannot bind local port {port} ({exc.strerror}). No processes were started.')
if not (root / 'frontend/dist/index.html').exists():
    raise SystemExit('Build the frontend first: cd frontend && npm ci && npm run build')
children = [subprocess.Popen([sys.executable, '-m', 'app.worker'], cwd=root),
            subprocess.Popen([sys.executable, '-m', 'uvicorn', 'app.api:app',
                              '--host', '127.0.0.1', '--port', str(port), '--no-access-log'], cwd=root)]


def stop(*_):
    for child in children:
        child.terminate()


signal.signal(signal.SIGTERM, stop)
signal.signal(signal.SIGINT, stop)
try:
    children[1].wait()
finally:
    stop()
    for child in children:
        try:
            child.wait(timeout=5)
        except subprocess.TimeoutExpired:
            child.kill()
