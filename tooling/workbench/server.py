"""Loopback-only review server. Run: uv run python -m tooling.workbench.server"""
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import argparse
import json
import mimetypes
from pathlib import Path
import urllib.parse
from tooling.review_store import Store,WORK
from tooling.discover import ROOT,PRIVATE

HTML=Path(__file__).with_name('index.html')


class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass # Never log source data, request bodies or credentials.
    def valid_host(self):return self.headers.get('Host') in {f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'}
    def reply(self,status,payload):
        raw=json.dumps(payload).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(raw)
    def do_GET(self):
        if not self.valid_host():self.reply(403,{'error':'Loopback host required'});return
        if self.path=='/':
            raw=HTML.read_bytes();self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store');self.send_header('X-Frame-Options','DENY');self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self'; media-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'");self.end_headers();self.wfile.write(raw);return
        store=Store(self.server.database)
        try:
            if self.path=='/api/catalog':self.reply(200,{'assets':store.assets(),'used_seconds':round(store.used_seconds(),3),'audit_valid':store.verify(),'active_session':store.active_session()});return
            if self.path.startswith('/media/'):
                identifier=urllib.parse.unquote(self.path[len('/media/'):]);asset=next((a for a in store.assets() if a['id']==identifier),None)
                if not asset:self.reply(404,{'error':'Asset not found'});return
                path=(ROOT/asset['local_path']).resolve()
                if not path.is_relative_to(PRIVATE.resolve()) or not path.is_file():self.reply(403,{'error':'Media path rejected'});return
                size=path.stat().st_size;start=0;end=size-1;status=200
                header=self.headers.get('Range')
                if header:
                    import re
                    match=re.fullmatch(r'bytes=(\d+)-(\d*)',header)
                    if not match:self.reply(416,{'error':'Unsupported range'});return
                    start=int(match[1]);end=min(int(match[2]) if match[2] else end,end)
                    if start>end:self.reply(416,{'error':'Range outside media'});return
                    status=206
                self.send_response(status);self.send_header('Content-Type',mimetypes.guess_type(path.name)[0] or 'application/octet-stream');self.send_header('Accept-Ranges','bytes');self.send_header('Content-Length',str(end-start+1));self.send_header('Cache-Control','private, no-store');self.send_header('X-Content-Type-Options','nosniff')
                if status==206:self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
                self.end_headers()
                with path.open('rb') as f:
                    f.seek(start);remaining=end-start+1
                    while remaining:
                        chunk=f.read(min(65536,remaining))
                        if not chunk:break
                        try:self.wfile.write(chunk)
                        except (BrokenPipeError,ConnectionResetError):break
                        remaining-=len(chunk)
                return
            self.reply(404,{'error':'Not found'})
        finally:store.close()
    def do_POST(self):
        origin=self.headers.get('Origin')
        if not self.valid_host() or origin not in {f'http://127.0.0.1:{self.server.server_port}',f'http://localhost:{self.server.server_port}'}:
            self.reply(403,{'error':'Same-origin local request required'});return
        if self.headers.get('Content-Type')!='application/json':self.reply(415,{'error':'JSON required'});return
        try:length=int(self.headers.get('Content-Length','0'))
        except ValueError:self.reply(400,{'error':'Invalid content length'});return
        if not 0<length<=20000:self.reply(413,{'error':'Request size rejected'});return
        store=Store(self.server.database)
        try:
            body=json.loads(self.rfile.read(length))
            if self.path=='/api/start':self.reply(200,{'session':store.start(body['asset_id'],body['actor'],body.get('role','owner'))})
            elif self.path=='/api/decision':self.reply(200,store.finish(body['session_id'],body['gate'],body['action'],body.get('reason',''),body.get('evidence','')))
            elif self.path=='/api/export':self.reply(200,store.export(WORK/'approved-media.json'))
            else:self.reply(404,{'error':'Unknown action'})
        except (ValueError,KeyError,TypeError) as error:self.reply(400,{'error':str(error)})
        finally:store.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--port',type=int,default=8765);parser.add_argument('--database',type=Path,default=WORK/'reviews.sqlite');args=parser.parse_args()
    store=Store(args.database);catalog=WORK/'catalog.json'
    if catalog.exists():store.sync(json.loads(catalog.read_text()))
    store.close();server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler);server.database=args.database
    print(f'Local curation: http://127.0.0.1:{server.server_port} (no deployment)',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:server.server_close()


if __name__=='__main__':main()
