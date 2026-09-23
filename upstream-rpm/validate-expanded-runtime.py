#!/usr/bin/env python3
"""Focused, offline runtime checks. Requires the disposable validation image."""
import base64, bz2, ctypes as C, fcntl, gzip, json, lzma, os, pathlib, pty
import select, signal, struct, subprocess as S, tempfile, termios, time, zlib
if not (pathlib.Path('/run/.containerenv').exists() or pathlib.Path('/.dockerenv').exists()):
    raise SystemExit('Disposable validation container required')
ROOT=pathlib.Path(tempfile.mkdtemp(prefix='expanded-runtime-',dir='/tmp'))
RESULTS=[]
def run(args, **kwargs):
    return S.check_output(args,stderr=S.STDOUT,timeout=30,**kwargs)
def passed(name):
    RESULTS.append(name);print('PASS',name,flush=True)
def fun(lib,name,result,args):
    f=getattr(lib,name);f.restype=result;f.argtypes=args;return f

payload=bytes(range(256))*1024
for module in (zlib,bz2,lzma,gzip):assert module.decompress(module.compress(payload))==payload
import xml.etree.ElementTree as ET, pyexpat
assert ET.fromstring('<r>한글 &amp; XML</r>').text=='한글 & XML'
assert pyexpat.EXPAT_VERSION=='expat_2.8.5'
passed('Python compression and Expat with combined set')

assert json.loads(run(['jq','-n','{a:("abc123"|capture("(?<n>[0-9]+)").n),b:([1,2,3]|add)}']))=={'a':'123','b':6}
passed('jq JSON and external Oniguruma regex')

import magic
m=magic.open(magic.MAGIC_MIME_TYPE);assert m.load()==0
assert m.file('/usr/bin/bash') in ('application/x-executable','application/x-pie-executable');m.close()
assert b'executable' in run(['file','--mime-type','/usr/bin/bash'])
passed('file and legacy Python magic API')

tasn=C.CDLL('libtasn1.so.6')
length=fun(tasn,'asn1_get_length_der',C.c_long,[C.c_void_p,C.c_int,C.POINTER(C.c_int)])
used=C.c_int();assert length(b'\x82\x01\x00'+b'\0'*256,259,C.byref(used))==256 and used.value==3
assert length(b'\x82\x01',2,C.byref(used))<0
passed('ASN.1 valid and truncated DER length')

import hashlib
crypt=C.CDLL('libgcrypt.so.20')
assert fun(crypt,'gcry_check_version',C.c_char_p,[C.c_char_p])(None)==b'1.12.4'
digest=C.create_string_buffer(32)
fun(crypt,'gcry_md_hash_buffer',None,[C.c_int,C.c_void_p,C.c_void_p,C.c_size_t])(8,digest,b'abc',3)
assert digest.raw==hashlib.sha256(b'abc').digest()
cipher=C.c_void_p()
assert fun(crypt,'gcry_cipher_open',C.c_uint,[C.POINTER(C.c_void_p),C.c_int,C.c_int,C.c_uint])(C.byref(cipher),7,1,0)==0
try:
    assert fun(crypt,'gcry_cipher_setkey',C.c_uint,[C.c_void_p,C.c_void_p,C.c_size_t])(cipher,b'\0'*16,16)==0
    encrypted=C.create_string_buffer(16)
    assert fun(crypt,'gcry_cipher_encrypt',C.c_uint,[C.c_void_p,C.c_void_p,C.c_size_t,C.c_void_p,C.c_size_t])(cipher,encrypted,16,b'\0'*16,16)==0
    assert encrypted.raw.hex()=='66e94bd4ef8a2c3b884cfa59ca342b2e'
finally:fun(crypt,'gcry_cipher_close',None,[C.c_void_p])(cipher)
passed('Libgcrypt SHA256 and AES known-answer vectors')

measure=ROOT/'time.txt'
run(['/usr/bin/time','-f','exit=%x','-o',str(measure),'/bin/sh','-c','exit 0'])
assert measure.read_text().strip()=='exit=0'
failed=S.run(['/usr/bin/time','-f','exit=%x','-o',str(measure),'/bin/sh','-c','exit 7'],stdout=S.PIPE,stderr=S.PIPE)
assert failed.returncode==7 and 'exit=7' in measure.read_text()
passed('GNU time child status and output format')

class XpmImage(C.Structure):
    _fields_=[('width',C.c_uint),('height',C.c_uint),('cpp',C.c_uint),('ncolors',C.c_uint),('colors',C.c_void_p),('data',C.POINTER(C.c_uint))]
xpm=C.CDLL('libXpm.so.4');im=XpmImage()
parse=fun(xpm,'XpmCreateXpmImageFromBuffer',C.c_int,[C.c_char_p,C.POINTER(XpmImage),C.c_void_p])
free=fun(xpm,'XpmFreeXpmImage',None,[C.POINTER(XpmImage)])
assert parse(b'/* XPM */\nstatic char *x[]={"2 2 2 1","a c #ff0000","b c #0000ff","ab","ba"};\n',C.byref(im),None)==0
assert (im.width,im.height,im.ncolors)==(2,2,2) and list(im.data[:4])==[0,1,1,0];free(C.byref(im))
passed('XPM image parser without a display')

packet=b'\x00'*12+b'\x08\x00'+bytes.fromhex('450000210001000040110000c0000201c0000202')+struct.pack('!HHHH',12345,53,13,0)+b'hello'
pcap=ROOT/'one.pcap';pcap.write_bytes(struct.pack('<IHHIIII',0xa1b2c3d4,2,4,0,0,65535,1)+struct.pack('<IIII',1,0,len(packet),len(packet))+packet)
capture=run(['tcpdump','-nn','-r',str(pcap),'udp and dst port 53'])
assert b'192.0.2.1.12345 > 192.0.2.2.53' in capture,capture
assert int(S.check_output(['tcpdump','-ddd','-y','EN10MB','tcp port 80'],stderr=S.PIPE,timeout=30).splitlines()[0])>0
passed('libpcap filter compile and tcpdump offline packet read')

nano_file=ROOT/'nano.txt'
pid,fd=pty.fork()
if pid==0:
    os.environ['TERM']='xterm';os.environ['LC_ALL']='C'
    os.execvp('nano',['nano','--ignorercfiles',str(nano_file)])
try:
    fcntl.ioctl(fd,termios.TIOCSWINSZ,struct.pack('HHHH',24,100,0,0))
    transcript=bytearray()
    def screen_until(token):
        end=time.monotonic()+10
        while time.monotonic()<end:
            if select.select([fd],[],[],0.2)[0]:transcript.extend(os.read(fd,65536))
            if token in transcript:return
        raise AssertionError('nano did not display '+repr(token))
    screen_until(b'nano')
    os.write(fd,b'expanded RPM test\x0f');screen_until(b'Write to File')
    os.write(fd,b'\r');screen_until(b'Wrote')
    os.write(fd,b'\x18')
    end=time.monotonic()+10
    while time.monotonic()<end:
        got,status=os.waitpid(pid,os.WNOHANG)
        if got:assert status==0;break
        time.sleep(0.1)
    else:raise AssertionError('nano exit timeout')
    assert nano_file.read_text()=='expanded RPM test\n'
finally:
    pathlib.Path('/results/nano-pty-transcript.bin').write_bytes(bytes(transcript))
    os.close(fd)
    try:os.kill(pid,signal.SIGTERM)
    except ProcessLookupError:pass
passed('nano interactive edit save and exit through PTY')

socket='linuxoss-runtime-'+str(os.getpid())
try:
    run(['tmux','-L',socket,'new-session','-d','-s','audit','/bin/bash'])
    run(['tmux','-L',socket,'send-keys','-t','audit','printf tmux-ok > '+str(ROOT/'tmux.txt')+'; tmux -L '+socket+' wait-for -S ready','Enter'])
    run(['tmux','-L',socket,'wait-for','ready'])
    assert (ROOT/'tmux.txt').read_text()=='tmux-ok'
finally:S.call(['tmux','-L',socket,'kill-server'],stdout=S.DEVNULL,stderr=S.DEVNULL)
passed('tmux isolated session and shell execution')

# A fresh local key and an explicitly trusted local certificate; no external hosts.
template=ROOT/'cert.cfg';template.write_text('cn = "localhost"\ndns_name = "localhost"\nexpiration_days = 1\ntls_www_server\nsigning_key\nencryption_key\n')
key=ROOT/'tls.key';cert=ROOT/'tls.crt'
run(['certtool','--generate-privkey','--bits','2048','--outfile',str(key)])
run(['certtool','--generate-self-signed','--load-privkey',str(key),'--template',str(template),'--outfile',str(cert)])
server=S.Popen(['openssl','s_server','-accept','127.0.0.1:24443','-cert',str(cert),'-key',str(key),'-www'],stdout=S.DEVNULL,stderr=S.DEVNULL)
try:
    time.sleep(0.3)
    result=run(['gnutls-cli','--x509cafile',str(cert),'-p','24443','localhost'],input=b'GET / HTTP/1.0\r\n\r\n')
    assert b'HTTP/1.0 200' in result,result[-1000:]
finally:server.terminate();server.wait(timeout=5)
passed('GnuTLS ASN.1 certificate parsing and trusted local TLS handshake')

sshkey=ROOT/'ssh-client';hostkey=ROOT/'ssh-host'
for p in (sshkey,hostkey):run(['ssh-keygen','-q','-t','rsa','-b','3072','-N','','-f',str(p)])
ssh_dir=pathlib.Path(tempfile.mkdtemp(prefix='ssh-fixture-',dir='/root'))
authorized=ssh_dir/'authorized_keys';authorized.write_bytes((ROOT/'ssh-client.pub').read_bytes());authorized.chmod(0o600)
config=ROOT/'sshd_config'
config.write_text('Port 22222\nListenAddress 127.0.0.1\nHostKey '+str(hostkey)+'\nAuthorizedKeysFile '+str(authorized)+'\nPermitRootLogin prohibit-password\nPasswordAuthentication no\nUsePAM no\nStrictModes yes\nPidFile '+str(ROOT/'sshd.pid')+'\n')
os.makedirs('/run/sshd',exist_ok=True)
# Unlock only the disposable container account with an unusable password hash.
# The loopback test server permits public-key authentication only.
run(['usermod','-p','x','root'])
server=S.Popen(['/usr/sbin/sshd','-D','-e','-f',str(config)],stdout=S.DEVNULL,stderr=(ROOT/'sshd.log').open('wb'))
lib=C.CDLL('libssh.so.4');ptr=C.c_void_p
session=fun(lib,'ssh_new',ptr,[])()
option=fun(lib,'ssh_options_set',C.c_int,[ptr,C.c_int,ptr])
channel=None;pubkey=ptr();exported=ptr()
try:
    time.sleep(0.3);assert server.poll() is None,(ROOT/'sshd.log').read_text()
    # SSH_OPTIONS_HOST=0, PORT=1, USER=4, IDENTITY=6 in the public API.
    port=C.c_uint(22222)
    for opt,val in ((0,C.c_char_p(b'127.0.0.1')),(1,C.byref(port)),(4,C.c_char_p(b'root')),(6,C.c_char_p(str(sshkey).encode()))):
        assert option(session,opt,val)==0
    assert fun(lib,'ssh_connect',C.c_int,[ptr])(session)==0
    assert fun(lib,'ssh_get_server_publickey',C.c_int,[ptr,C.POINTER(ptr)])(session,C.byref(pubkey))==0
    assert fun(lib,'ssh_pki_export_pubkey_base64',C.c_int,[ptr,C.POINTER(ptr)])(pubkey,C.byref(exported))==0
    assert C.string_at(exported)==(ROOT/'ssh-host.pub').read_bytes().split()[1], 'Server host key mismatch'
    assert fun(lib,'ssh_userauth_publickey_auto',C.c_int,[ptr,C.c_char_p,C.c_char_p])(session,None,None)==0
    channel=fun(lib,'ssh_channel_new',ptr,[ptr])(session)
    assert fun(lib,'ssh_channel_open_session',C.c_int,[ptr])(channel)==0
    assert fun(lib,'ssh_channel_request_exec',C.c_int,[ptr,C.c_char_p])(channel,b'printf libssh-command-ok')==0
    buf=C.create_string_buffer(256)
    n=fun(lib,'ssh_channel_read_timeout',C.c_int,[ptr,ptr,C.c_uint32,C.c_int,C.c_int])(channel,buf,len(buf),0,5000)
    assert buf.raw[:n]==b'libssh-command-ok',(n,buf.raw[:n])
finally:
    if exported:fun(lib,'ssh_string_free_char',None,[ptr])(exported)
    if pubkey:fun(lib,'ssh_key_free',None,[ptr])(pubkey)
    if channel:fun(lib,'ssh_channel_free',None,[ptr])(channel)
    if session:
        fun(lib,'ssh_disconnect',None,[ptr])(session);fun(lib,'ssh_free',None,[ptr])(session)
    server.terminate();server.wait(timeout=5)
passed('libssh pinned host key public-key login and local command execution')

java=ROOT/'CombinedJavaCheck.java'
java.write_text('''import java.io.*; import java.awt.*; import java.awt.image.*; import javax.imageio.*; import java.util.*; import java.util.zip.*;
public class CombinedJavaCheck { public static void main(String[] args) throws Exception {
 BufferedImage im=new BufferedImage(80,30,BufferedImage.TYPE_INT_RGB); Graphics2D g=im.createGraphics();
 g.setColor(Color.WHITE);g.fillRect(0,0,80,30);g.setColor(Color.BLACK);g.drawString("Java 8 test",2,20);g.dispose();
 ByteArrayOutputStream b=new ByteArrayOutputStream();if(!ImageIO.write(im,"jpeg",b))throw new AssertionError();
 BufferedImage d=ImageIO.read(new ByteArrayInputStream(b.toByteArray()));if(d.getWidth()!=80||d.getHeight()!=30)throw new AssertionError();
 byte[] data=new byte[65536];new Random(123).nextBytes(data);b.reset();try(GZIPOutputStream z=new GZIPOutputStream(b)){z.write(data);}
 ByteArrayOutputStream out=new ByteArrayOutputStream();try(GZIPInputStream z=new GZIPInputStream(new ByteArrayInputStream(b.toByteArray()))){byte[] a=new byte[4096];int n;while((n=z.read(a))!=-1)out.write(a,0,n);}
 if(!Arrays.equals(data,out.toByteArray()))throw new AssertionError();System.out.println("JAVA8_IMAGE_FONT_GZIP_OK"); }}''')
run(['javac',str(java)]);assert b'JAVA8_IMAGE_FONT_GZIP_OK' in run(['java','-Djava.awt.headless=true','-cp',str(ROOT),'CombinedJavaCheck'])
passed('Java 8 headless font draw JPEG and gzip roundtrips')

source=ROOT/'source';source.mkdir(exist_ok=True);(source/'file').write_bytes(payload)
os.symlink('file',str(source/'link'));os.link(str(source/'file'),str(source/'hard'))
shell=ROOT/'local-shell';shell.write_text('#!/bin/bash\nshift\nexec "$@"\n');shell.chmod(0o755)
run(['rsync','-aH','-e',str(shell),'--rsync-path=/tmp/rsync-before',str(source)+'/', 'localhost:'+str(ROOT/'dest')+'/'])
assert (ROOT/'dest/file').read_bytes()==payload
assert (ROOT/'dest/file').stat().st_ino==(ROOT/'dest/hard').stat().st_ino
assert os.readlink(str(ROOT/'dest/link'))=='file'
passed('rsync new-to-old peer content symlink and hardlink')
run(['rpm','-qa']);run(['dnf','--disableplugin=subscription-manager','--disablerepo=*','check'])
passed('RPM and DNF consumers after popt and compression upgrades')
pathlib.Path('/results/runtime-checks.json').write_text(json.dumps({'passed':RESULTS,'actual_target_tested':False},indent=2))
