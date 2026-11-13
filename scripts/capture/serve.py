"""Local capture adapter: serve the repo and accept only numbered PNG frames."""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re
import sys
ROOT = Path(__file__).resolve().parents[2]
OUTPUT = Path(sys.argv[1]).resolve()
class Capture(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)
    def do_POST(self):
        match = re.fullmatch(r'/frame/([a-z0-9-]+)/([0-9]{3})', self.path)
        if not match:
            self.send_error(404); return
        size = int(self.headers.get('Content-Length', 0))
        if not 0 < size < 16 * 1024 * 1024:
            self.send_error(413); return
        dest = OUTPUT / match[1] / (match[2] + '.png')
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(self.rfile.read(size))
        self.send_response(204); self.end_headers()
    def log_message(self, *args):
        pass
print('Capture server: http://127.0.0.1:5190/scripts/capture/jelly.html', flush=True)
ThreadingHTTPServer(('127.0.0.1', 5190), Capture).serve_forever()
