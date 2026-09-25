"""Installed-binary checks for the disposable EL8 reference image."""
import io,json,os,subprocess,tempfile,tarfile,threading
from http.server import BaseHTTPRequestHandler,HTTPServer
from pathlib import Path
records=[]
def run(args,expected=0,cwd=None):
    result=subprocess.run(args,cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=30)
    records.append(dict(command=args,exit=result.returncode,stdout=result.stdout,stderr=result.stderr))
    assert result.returncode==expected,records[-1]
    return result.stdout
with tempfile.TemporaryDirectory() as work:
    root=Path(work)
    (root/'a.jq').write_text('include "b"; def foo: 1;\n')
    (root/'b.jq').write_text('include "a"; def bar: 2;\n')
    cycle=subprocess.run(['jq','-L',work,'-n','include "a"; foo'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=20)
    records.append(dict(test='jq-mutual-include-CVE-2026-44777',exit=cycle.returncode,stderr=cycle.stderr))
    assert cycle.returncode>0 and ('circular' in cycle.stderr.lower() or 'cycle' in cycle.stderr.lower() or 'depth' in cycle.stderr.lower()),records[-1]
    (root/'b.jq').write_text('def bar: 2;\n');assert run(['jq','-L',work,'-n','include "a"; foo']).strip()=='1'
    if os.environ.get('JQ_ONLY')!='1':
        assert '42' in run(['gdb','--batch','-nx','-ex','python print(6 * 7)'])
        run(['gdbserver','--version']);run(['eu-readelf','-h','/usr/bin/ls']);run(['debuginfod-find','--version'])
        assert run(['pkg-config','--modversion','libarchive']).strip()=='3.8.9'
        run(['vim','-Nu','NONE','-i','NONE','-n','-es','-c','call writefile([string(6 * 7)], "result")','-c','qa!'],cwd=work)
        assert (root/'result').read_text().strip()=='42'
        assert run(['csh','-f','-c','echo 42']).strip()=='42'
        run(['unzip','-v']);run(['dig','-v'])
        run(['ld','--version']);run(['as','--version']);run(['nmap','--version']);run(['ncat','--version'])
        run(['ping','-V'])
        run(['gdk-pixbuf-query-loaders-64'])
        # ELF linking for a real consumer checks pkgconf + libarchive headers.
        (root/'link.c').write_text('#include <archive.h>\nint main(void){struct archive *a=archive_read_new();return archive_read_free(a);}\n')
        flags=run(['pkg-config','--cflags','--libs','libarchive']).split()
        run(['gcc',str(root/'link.c'),'-o',str(root/'link')]+flags);run([str(root/'link')])
        # Extraction jail must also work when the EL8 kernel lacks openat2.
        jail=root/'jail';outside=root/'outside';jail.mkdir();outside.mkdir()
        (jail/'escape').symlink_to(outside,target_is_directory=True)
        with tarfile.open(str(root/'escape.tar'),'w') as archive:
            member=tarfile.TarInfo('escape/created');member.size=4
            archive.addfile(member,io.BytesIO(b'test'))
        blocked=subprocess.run(['tar','-xf',str(root/'escape.tar'),'-C',str(jail)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=10)
        assert not (outside/'created').exists(), 'tar escaped extraction root'
        records.append(dict(test='tar-symlink-extraction-jail',exit=blocked.returncode,stderr=blocked.stderr))
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200);self.send_header('Content-Length','8');self.end_headers();self.wfile.write(b'wget-ok\n')
            def log_message(self,*args):pass
        server=HTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever);thread.daemon=True;thread.start()
        try:
            run(['wget','--no-proxy','--timeout=5','--tries=1','-q','-O',str(root/'download'),'http://127.0.0.1:'+str(server.server_port)+'/'])
            assert (root/'download').read_bytes()==b'wget-ok\n'
        finally:server.shutdown();server.server_close()
out=Path('/next/jq-check.json' if os.environ.get('JQ_ONLY')=='1' else '/next/runtime-validation/smoke.json')
out.write_text(json.dumps(records,indent=2)+'\n')
print('INSTALLED_BINARY_SMOKE_OK',len(records))
