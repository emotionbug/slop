#!/usr/bin/env python3
"""Focused tests for the next RPM group, inside a disposable EL8 container."""
import ctypes,hashlib,json,os,pathlib,re,signal,subprocess,tarfile,tempfile
assert pathlib.Path('/run/.containerenv').exists() or pathlib.Path('/.dockerenv').exists()
work=pathlib.Path(tempfile.mkdtemp(prefix='linuxoss-wave6-'))
checks=[]
def run(cmd,**kw):
 data=kw.pop('input',None)
 process=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
   stdin=subprocess.PIPE if data is not None else None,start_new_session=True,**kw)
 try:output,_=process.communicate(data,timeout=90)
 except subprocess.TimeoutExpired:
  os.killpg(process.pid,signal.SIGKILL);output,_=process.communicate()
  print(output.decode(errors='replace'),flush=True);raise
 if process.returncode:
  print(output.decode(errors='replace'),flush=True)
  raise subprocess.CalledProcessError(process.returncode,cmd,output)
 return output.decode()
def done(name):checks.append(name);print('PASS',name,flush=True)

# Exercise package selection with the installed libdnf/hawkey consuming new libsolv.
run(['dnf','--disableplugin=subscription-manager','--disablerepo=*','check'])
out=run(['dnf','--disableplugin=subscription-manager','--disablerepo=*','list','installed','coreutils','protobuf-c'])
assert '9.12' in out and '1.5.2' in out,out
run(['/usr/libexec/platform-python','-c','import hawkey; s=hawkey.Sack(); s.load_system_repo(); assert len(list(hawkey.Query(s)))>100'])
done('DNF check and libdnf/hawkey system RPM database query')

pc=ctypes.CDLL('libprotobuf-c.so.1');pc.protobuf_c_version.restype=ctypes.c_char_p
assert pc.protobuf_c_version()==b'1.5.2'
assert pc.protobuf_c_version_number()==1005002
done('Installed protobuf-c public version API')

sample=work/'source';payload=bytes(range(256))*32;sample.write_bytes(payload)
run(['cp','--reflink=auto','--preserve=mode,timestamps',str(sample),str(work/'copy')])
assert (work/'copy').read_bytes()==payload
assert run(['sha256sum',str(sample)]).split()[0]==hashlib.sha256(payload).hexdigest()
assert run(['sort','-n'],input=b'3\n1\n2\n')=='1\n2\n3\n'
assert run(['date','-u','-d','2026-09-24 00:00:00','+%Y-%m-%d'])=='2026-09-24\n'
assert run(['timeout','2','sh','-c','printf ok'])=='ok'
assert run(['/usr/sbin/chroot','--version']).startswith('chroot (GNU coreutils) 9.12')
assert run(['arch'])==run(['uname','-m'])
assert subprocess.run(['arch','--invalid-option'],stdout=subprocess.PIPE,stderr=subprocess.PIPE).returncode!=0
# Preserve binary data through stdbuf without text decoding.
assert subprocess.check_output(['stdbuf','-oL','cat',str(sample)],timeout=10)==payload
assert pathlib.Path('/etc/profile.d/colorls.sh').exists()
done('Coreutils copy/hash/sort/date/timeout/stdbuf and EL8 chroot path')

def check_mtr():
 archive=pathlib.Path('/recipe/sources/mtr-0.96.tar.gz')
 assert hashlib.sha256(archive.read_bytes()).hexdigest()=='ffd19a9f8d5f616c1ea2f0da9fbf9d1239bcecdf5a68912e831966d20929037a'
 with tarfile.open(str(archive)) as source:
  for name in ['test/cmdparse.py','test/param.py','test/mtrpacket.py','test/packet_listen.c','packet/protocols.h','packet/probe_unix.h']:
   target=work/name;target.parent.mkdir(parents=True,exist_ok=True)
   target.write_bytes(source.extractfile('mtr-0.96/'+name).read())
 tests=work/'test'
 # 0.96 changed the first probe sequence to MIN_PORT=33434, while its test
 # listener still expects 33000. Correct only that stale fixture constant.
 first_sequence=int(re.search(r'^#define MIN_PORT (\d+)$',(work/'packet/probe_unix.h').read_text(),re.M).group(1))
 listener=tests/'packet_listen.c';text=listener.read_text()
 assert text.count('#define SEQUENCE_NUM 33000')==1 and first_sequence==33434
 listener.write_text(text.replace('#define SEQUENCE_NUM 33000','#define SEQUENCE_NUM '+str(first_sequence)))
 print('MTR fixture sequence aligned with upstream MIN_PORT='+str(first_sequence),flush=True)
 run(['gcc','-O2','-I'+str(work),str(tests/'packet_listen.c'),'-o',str(work/'mtr-packet-listen')])
 # Only the suite's IPv6-availability DNS probe is redirected to loopback.
 # Remote probe.py is intentionally excluded from this isolated local test.
 p=tests/'mtrpacket.py';s=p.read_text();assert s.count("IPV6_TEST_HOST = 'google-public-dns-a.google.com'")==1
 p.write_text(s.replace("IPV6_TEST_HOST = 'google-public-dns-a.google.com'","IPV6_TEST_HOST = '::1'"))
 env=dict(os.environ,MTR_PACKET='/usr/sbin/mtr-packet')
 for suite in ['cmdparse.py','param.py']:
  result=run(['/usr/bin/python3',str(tests/suite)],cwd=str(work),env=env)
  print(result,flush=True)
  assert re.search(r'Ran \d+ tests?',result) and '\nOK' in result,result
 result=run(['/usr/sbin/mtr','--report','--report-cycles','2','--no-dns','127.0.0.1'])
 assert '127.0.0.1' in result and '0.0%' in result,result
 done('MTR installed-RPM parser/parameter suites and loopback ICMP')


if os.environ.get('CHECK_MTR')=='1':check_mtr()

lib=ctypes.CDLL('libjbig2dec.so.0')
lib.jbig2_ctx_new_imp.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_int,ctypes.c_int]
lib.jbig2_ctx_new_imp.restype=ctypes.c_void_p
lib.jbig2_ctx_free.argtypes=[ctypes.c_void_p]
ctx=lib.jbig2_ctx_new_imp(None,0,None,None,None,0,20);assert ctx
lib.jbig2_ctx_free(ctx)
done('Installed JBIG2 decoder context create/free API')
pathlib.Path('/results/runtime-checks.json').write_text(json.dumps({'status':'passed','checks':checks,
 'limits':['No target deployment','MTR is excluded from the bundle: an optional CHECK_MTR=1 reproducer retains the packet-size test failure; remote probes were not run','Four upstream JBIG2 test programs passed; target Ghostscript was not tested']},indent=2))
