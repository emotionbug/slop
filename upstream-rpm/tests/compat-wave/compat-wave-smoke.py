"""Run installed compatibility/security regressions in a disposable EL8 container."""
from pathlib import Path
import ctypes,json,os,shutil,struct,subprocess,tempfile
assert Path('/run/.containerenv').exists() or Path('/.dockerenv').exists()
out=Path('/next/runtime-validation');out.mkdir(exist_ok=True)
results=[]
def run(name,args,cwd=None,env=None):
 p=subprocess.run(args,cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,universal_newlines=True,timeout=180)
 (out/(name+'.log')).write_text(p.stdout)
 results.append(dict(test=name,passed=p.returncode==0,exit_code=p.returncode))
 print(name,p.returncode,flush=True)
 if p.returncode:raise RuntimeError(name+': '+p.stdout[-2000:])
 return p.stdout
try:
 tools=list(Path('/next/install-kit/rpms').glob('libtiff-tools-*.rpm'));assert len(tools)==1
 run('tiff-tools-disposable-install',['dnf','-y','--noplugins','--disablerepo=*','install',str(tools[0])])
 run('dnf-check',['dnf','--noplugins','--disablerepo=*','check'])
 run('el8-precompiled-consumer',['xvfb-run','-a','/usr/local/bin/linuxoss-old-abi-consumer'])
 errors=[];loader_contexts=[]
 for path in json.loads((out/'changed-libraries.json').read_text()):
  env=dict(os.environ)
  if Path(path).name.startswith(('libevent_extra-','libevent_pthreads-','libevent_openssl-')):
   # The upstream split libraries intentionally leave core symbols to the
   # consumer's -levent link, as also declared by EL8 pkg-config metadata.
   env['LD_PRELOAD']='/usr/lib64/libevent-2.1.so.6'
   loader_contexts.append(dict(path=path,provider=env['LD_PRELOAD'],reason='libevent split-library core link contract'))
  p=subprocess.run(['ldd','-r',path],env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,universal_newlines=True)
  if p.returncode or 'undefined symbol:' in p.stdout or 'not found' in p.stdout:errors.append(dict(path=path,output=p.stdout))
 (out/'loader-errors.json').write_text(json.dumps(errors,indent=2))
 (out/'loader-contexts.json').write_text(json.dumps(loader_contexts,indent=2))
 results.append(dict(test='changed-library-loaders',passed=not errors,count=len(json.loads((out/'changed-libraries.json').read_text()))))
 assert not errors,errors[:2]
 with tempfile.TemporaryDirectory(prefix='linuxoss-smoke-') as tmp:
  d=Path(tmp)
  (d/'event-split.c').write_text('''#include <event2/event.h>
#include <event2/thread.h>
#include <event2/http.h>
#include <assert.h>
int main(){assert(evthread_use_pthreads()==0);struct event_base *b=event_base_new();assert(b);struct evhttp *h=evhttp_new(b);assert(h);evhttp_free(h);event_base_free(b);return 0;}
''')
  run('libevent-split-link',['gcc','event-split.c','-levent_extra','-levent_pthreads','-levent','-o','event-split'],tmp)
  run('libevent-split-http-thread-control',['./event-split'],tmp)
  (d/'lto.c').write_text('int lto(void){return 40;}\n')
  (d/'native.c').write_text('int native(void){return 2;}\n')
  (d/'main.c').write_text('int lto(void);int native(void);int main(void){return lto()+native()!=42;}\n')
  run('gcc8-lto-compile',['gcc','-flto','-c','lto.c'],tmp)
  run('gcc8-native-compile',['gcc','-c','native.c'],tmp)
  run('gcc8-mixed-partial-link',['gcc','-nostdlib','-flto','-r','lto.o','native.o','-o','partial.o'],tmp)
  run('gcc8-lto-final-link',['gcc','-flto','main.c','partial.o','-o','lto-test'],tmp)
  run('gcc8-lto-execute',['./lto-test'],tmp)
  (d/'cpp.cc').write_text('#include <iostream>\nint main(){std::cout << 42;return 0;}\n')
  run('gxx8-lto-link',['g++','-flto','cpp.cc','-o','cpp-test'],tmp)
  assert run('gxx8-lto-execute',['./cpp-test'],tmp)=='42'
  lib=ctypes.CDLL('libidn.so.11');lib.idna_to_unicode_8z8z.argtypes=[ctypes.c_char_p,ctypes.POINTER(ctypes.c_void_p),ctypes.c_int]
  libc=ctypes.CDLL(None);libc.free.argtypes=[ctypes.c_void_p]
  for value,expected in [(b'xn--XXXXcom--.xn--com-',b'xn--XXXXcom--.xn--com-'),(b'xn--bcher-kva.de','b\u00fccher.de'.encode())]:
   p=ctypes.c_void_p();assert lib.idna_to_unicode_8z8z(value,ctypes.byref(p),0)==0
   try:assert ctypes.string_at(p)==expected
   finally:libc.free(p)
  results.append(dict(test='libidn-57053-ace-prefix-and-control',passed=True))
  (d/'empty.c').write_text('/* A valid BPF ELF with no programs. */\n')
  run('libbpf-empty-elf-compile',['gcc','-c','empty.c','-o','empty-native.o'],tmp)
  # An empty C translation unit has zero-size .bss/.data sections which
  # libbpf treats as invalid zero-length maps. A no-program BPF fixture omits them.
  run('libbpf-empty-elf-sections',['objcopy','-R','.text','-R','.data','-R','.bss','-R','.comment','-R','.note.GNU-stack','-R','.note.gnu.property','empty-native.o','empty.o'],tmp)
  elf=bytearray((d/'empty.o').read_bytes());struct.pack_into('<H',elf,18,247)
  (d/'empty-bpf.o').write_bytes(elf)
  shoff=struct.unpack_from('<Q',elf,40)[0];count=struct.unpack_from('<H',elf,60)[0]
  struct.pack_into('<H',elf,60,0);struct.pack_into('<Q',elf,shoff+32,count)
  (d/'extended-bpf.o').write_bytes(elf)
  (d/'bpf-test.c').write_text('''#include <bpf/libbpf.h>
#include <assert.h>
int main(int argc,char **argv){for(int i=1;i<argc;i++){struct bpf_object *o=bpf_object__open_file(argv[i],0);assert(o&&!libbpf_get_error(o));assert(bpf_object__next_program(o,0)==0);bpf_object__close(o);}char bad[64]={0};struct bpf_object *badobj=bpf_object__open_mem(bad,sizeof(bad),0);assert(!badobj||libbpf_get_error(badobj));return 0;}
''')
  run('libbpf-regression-compile',['gcc','bpf-test.c','-lbpf','-o','bpf-test'],tmp)
  run('libbpf-extended-sections-empty-program-malformed',['./bpf-test','empty-bpf.o','extended-bpf.o'],tmp)
  (d/'gtk-probe.c').write_text('#include <gtk/gtk.h>\nint main(int argc,char**argv){gtk_init(&argc,&argv);return 0;}\n')
  flags=subprocess.check_output(['pkg-config','--cflags','--libs','gtk+-2.0'],universal_newlines=True).split()
  run('gtk-probe-compile',['gcc','gtk-probe.c','-o','gtk-probe']+flags,tmp)
  (d/'module.c').write_text('#include <stdio.h>\n__attribute__((constructor)) static void mark(void){FILE *f=fopen("MODULE_LOADED","w");if(f){fputs("loaded",f);fclose(f);}}\nvoid gtk_module_init(void){}\n')
  run('gtk-module-compile',['gcc','-shared','-fPIC','module.c','-o','liblinuxoss-module.so'],tmp)
  env=dict(os.environ,GTK_MODULES='./linuxoss-module')
  run('gtk-cwd-module-rejected',['xvfb-run','-a','./gtk-probe'],tmp,env)
  assert not (d/'MODULE_LOADED').exists(),'GTK loaded relative cwd module'
  env['GTK_MODULES']=str(d/'liblinuxoss-module.so')
  run('gtk-explicit-absolute-module-control',['xvfb-run','-a','./gtk-probe'],tmp,env)
  assert (d/'MODULE_LOADED').is_file(),'GTK positive control did not load'
  run('gdk-loader-cache',['gdk-pixbuf-query-loaders-64'])
  (d/'pixbuf-jpeg.c').write_text('''#include <gdk-pixbuf/gdk-pixbuf.h>
#include <assert.h>
int main(){GError *e=0;GdkPixbuf *p=gdk_pixbuf_new(GDK_COLORSPACE_RGB,0,8,4,4);assert(p);gdk_pixbuf_fill(p,0xff0000ff);assert(gdk_pixbuf_save(p,"pixbuf.jpg","jpeg",&e,0));g_object_unref(p);p=gdk_pixbuf_new_from_file("pixbuf.jpg",&e);assert(p&&gdk_pixbuf_get_width(p)==4);g_object_unref(p);return 0;}
''')
  flags=subprocess.check_output(['pkg-config','--cflags','--libs','gdk-pixbuf-2.0'],universal_newlines=True).split()
  run('gdk-jpeg-regression-compile',['gcc','pixbuf-jpeg.c','-o','pixbuf-jpeg']+flags,tmp)
  run('gdk-builtin-jpeg-roundtrip',['./pixbuf-jpeg'],tmp)
  (d/'sample.ppm').write_bytes(b'P6\n2 2\n255\n'+bytes([255,0,0])*4)
  run('openjpeg-encode',['opj_compress','-i','sample.ppm','-o','sample.j2k','-n','1'],tmp)
  run('openjpeg-decode',['opj_decompress','-i','sample.j2k','-o','decoded.ppm'],tmp)
  assert (d/'decoded.ppm').stat().st_size>12
  p=subprocess.run(['tiffcrop','-S','4294967295:4294967295','/tmp/linuxoss-abi.tif',str(d/'bad-crop.tif')],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,universal_newlines=True,timeout=15)
  (out/'tiffcrop-subdivision-overflow.log').write_text(p.stdout)
  assert p.returncode!=0 and 'Limit for subdivisions' in p.stdout,p.stdout
  results.append(dict(test='tiffcrop-52490-overflow-rejected',passed=True))
  run('tiffcrop-subdivision-control',['tiffcrop','-H','72','-V','72','-S','1:1','/tmp/linuxoss-abi.tif',str(d/'good-crop.tif')])
  (d/'pixar-test.c').write_text('''#include <tiffio.h>
#include <assert.h>
#include <string.h>
int main(){TIFF *t=TIFFOpen("pixar.tif","w");assert(t);
assert(TIFFSetField(t,TIFFTAG_IMAGEWIDTH,1));assert(TIFFSetField(t,TIFFTAG_IMAGELENGTH,2));assert(TIFFSetField(t,TIFFTAG_SAMPLESPERPIXEL,3));assert(TIFFSetField(t,TIFFTAG_BITSPERSAMPLE,8));assert(TIFFSetField(t,TIFFTAG_ROWSPERSTRIP,2));assert(TIFFSetField(t,TIFFTAG_PLANARCONFIG,PLANARCONFIG_CONTIG));assert(TIFFSetField(t,TIFFTAG_PHOTOMETRIC,PHOTOMETRIC_RGB));assert(TIFFSetField(t,TIFFTAG_COMPRESSION,COMPRESSION_PIXARLOG));assert(TIFFSetField(t,TIFFTAG_PIXARLOGDATAFMT,PIXARLOGDATAFMT_8BIT));unsigned char input[6]={255,0,0,0,255,0};assert(TIFFWriteEncodedStrip(t,0,input,6)>0);TIFFClose(t);
t=TIFFOpen("pixar.tif","r");assert(t);assert(TIFFSetField(t,TIFFTAG_PIXARLOGDATAFMT,PIXARLOGDATAFMT_8BITABGR));unsigned char guarded[32];memset(guarded,0xA5,sizeof guarded);TIFFReadEncodedStrip(t,0,guarded+8,6);for(int i=0;i<8;i++)assert(guarded[i]==0xA5);for(int i=14;i<32;i++)assert(guarded[i]==0xA5);TIFFClose(t);return 0;}
''')
  run('tiff-pixar-regression-compile',['gcc','pixar-test.c','-ltiff','-o','pixar-test'],tmp)
  run('tiff-pixar-12912-output-bounds',['./pixar-test'],tmp)
  (d/'data').write_bytes(b'linuxoss compatibility\n'*1000)
  run('brotli-compress',['brotli','data','-o','data.br'],tmp)
  run('brotli-decompress',['brotli','-d','data.br','-o','restored'],tmp)
  assert (d/'data').read_bytes()==(d/'restored').read_bytes()
  shutil.copytree('/recipe/work/mtr-upstream-test',d/'mtr')
  harness=d/'mtr/mtrpacket.py'
  harness.write_text(harness.read_text().replace("IPV6_TEST_HOST = 'google-public-dns-a.google.com'","IPV6_TEST_HOST = '::1'"))
  run('mtr-test-listener-compile',['gcc','-I.','packet_listen.c','-o','mtr-packet-listen'],str(d/'mtr'))
  env=dict(os.environ,MTR_PACKET='/usr/sbin/mtr-packet')
  run('mtr-upstream-command-and-loopback-packets',['/usr/libexec/platform-python','-m','unittest','cmdparse','param'],str(d/'mtr'),env)
  run('mtr-localhost-report',['mtr','--report','--report-cycles','2','--no-dns','127.0.0.1'])
 print('INSTALLED_COMPATIBILITY_REGRESSIONS_PASSED',flush=True)
finally:
 (out/'smoke-results.json').write_text(json.dumps(results,indent=2)+'\n')
