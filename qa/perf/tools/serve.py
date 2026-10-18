# static server emulating GitHub Pages: gzip, ETag (304), Cache-Control: max-age=600. usage: serve.py <root> <port>
import http.server,gzip,hashlib,os,sys,functools
ROOT,PORT=sys.argv[1],int(sys.argv[2]); CACHE={}
class H(http.server.SimpleHTTPRequestHandler):
  def log_message(self,*a): pass
  def do_GET(self):
    path=self.translate_path(self.path.split('?')[0])
    if os.path.isdir(path): path=os.path.join(path,'index.html')
    if not os.path.isfile(path): return self.send_error(404)
    st=os.stat(path); key=(path,st.st_mtime,st.st_size)
    if key not in CACHE:
      raw=open(path,'rb').read(); CACHE[key]=(raw,gzip.compress(raw,6),'"%s"'%hashlib.md5(raw).hexdigest())
    raw,gz,et=CACHE[key]
    if self.headers.get('If-None-Match')==et:
      self.send_response(304); self.send_header('ETag',et); self.send_header('Cache-Control','max-age=600'); self.end_headers(); return
    usegz='gzip' in (self.headers.get('Accept-Encoding') or '') and not path.endswith(('.png','.jpg'))
    body=gz if usegz else raw
    self.send_response(200); self.send_header('Content-Type',self.guess_type(path)); self.send_header('Content-Length',str(len(body)))
    if usegz: self.send_header('Content-Encoding','gzip')
    self.send_header('ETag',et); self.send_header('Cache-Control','max-age=600'); self.end_headers(); self.wfile.write(body)
http.server.ThreadingHTTPServer(('127.0.0.1',PORT),functools.partial(H,directory=ROOT)).serve_forever()
