#!/usr/bin/env bash
# Explicit private-loader tests only; this does not replace the system libc.
set -euo pipefail
[[ -e /run/.containerenv || -e /.dockerenv ]] || exit 2
[[ $(id -u) == 0 ]] || exit 2
package=/packages/glibc-evaluation-clean/linuxoss-glibc-evaluation-2.44-1.linuxoss.el8.x86_64.rpm
dnf -y --disableplugin=subscription-manager --disablerepo='*' \
  --setopt=localpkg_gpgcheck=False --setopt=install_weak_deps=False install "$package"
dnf --disableplugin=subscription-manager --disablerepo='*' check
prefix=/opt/linux-oss/glibc-2.44
loader="$prefix/lib/ld-linux-x86-64.so.2"
paths="$prefix/lib:/usr/lib64"
"$loader" --library-path "$paths" /usr/bin/getconf GNU_LIBC_VERSION
"$loader" --library-path "$paths" /usr/bin/getent passwd root | grep -q '^root:'
"$loader" --library-path "$paths" /usr/bin/getent hosts localhost
work=$(mktemp -d /tmp/glibc-evaluation.XXXXXX)
cd "$work"
"$loader" --library-path "$paths" /usr/bin/python3 - <<'PY'
import concurrent.futures,ctypes,hashlib,os,pwd,socket,sqlite3,ssl,zlib
libc=ctypes.CDLL(None);libc.gnu_get_libc_version.restype=ctypes.c_char_p
assert libc.gnu_get_libc_version()==b'2.44'
assert '/opt/linux-oss/glibc-2.44/lib/libc.so.6' in open('/proc/self/maps').read()
assert pwd.getpwuid(0).pw_name=='root'
assert socket.getaddrinfo('localhost',0)
data=bytes(range(256))*4096
assert zlib.decompress(zlib.compress(data))==data
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
    results=list(pool.map(lambda _:hashlib.sha256(data).digest(),range(128)))
assert len(set(results))==1
db=sqlite3.connect(':memory:');db.execute('create table test(x integer)')
db.executemany('insert into test values (?)',[(i,) for i in range(100)])
assert db.execute('select sum(x) from test').fetchone()[0]==4950
assert len(ssl.RAND_bytes(32))==32
print('GLIBC244_EL8_PYTHON_THREADS_NSS_SQLITE_ZLIB_SSL_OK',ssl.OPENSSL_VERSION)
PY
cat > GlibcRuntime.java <<'JAVA'
import java.nio.file.*;
import java.security.*;
import java.util.*;
import java.util.concurrent.*;
import java.util.zip.*;
public class GlibcRuntime {
 public static void main(String[] args) throws Exception {
  String maps=new String(Files.readAllBytes(Paths.get("/proc/self/maps")),"UTF-8");
  if(!maps.contains("/opt/linux-oss/glibc-2.44/lib/libc.so.6"))throw new AssertionError("wrong libc");
  byte[] data=new byte[1048576];new Random(42).nextBytes(data);
  Deflater d=new Deflater();d.setInput(data);d.finish();byte[] compressed=new byte[data.length+65536];
  int n=d.deflate(compressed);if(!d.finished())throw new AssertionError();d.end();
  Inflater i=new Inflater();i.setInput(compressed,0,n);byte[] result=new byte[data.length];
  int size=i.inflate(result);if(!i.finished()||size!=data.length||!Arrays.equals(data,result))throw new AssertionError();i.end();
  KeyPairGenerator g=KeyPairGenerator.getInstance("RSA");g.initialize(2048);KeyPair pair=g.generateKeyPair();
  Signature sig=Signature.getInstance("SHA256withRSA");sig.initSign(pair.getPrivate());sig.update(data);byte[] signed=sig.sign();
  sig.initVerify(pair.getPublic());sig.update(data);if(!sig.verify(signed))throw new AssertionError();
  ExecutorService pool=Executors.newFixedThreadPool(8);
  try {List<Future<byte[]>> jobs=new ArrayList<>();for(int k=0;k<128;k++)jobs.add(pool.submit(()->MessageDigest.getInstance("SHA-256").digest(data)));
    byte[] expected=jobs.get(0).get();for(Future<byte[]> job:jobs)if(!Arrays.equals(expected,job.get()))throw new AssertionError();
  } finally {pool.shutdown();}
  System.out.println("GLIBC244_EL8_JAVA8_THREADS_RSA_ZLIB_OK");
 }
}
JAVA
javac GlibcRuntime.java
java_binary=$(readlink -f /usr/bin/java)
# Java 8's launcher derives its JRE location from /proc/self/exe. With an
# explicitly invoked loader that path points at the loader, not java.
# Copy only the evaluation loader beside the unchanged java executable in
# this disposable container, so launcher-relative JRE discovery still works.
java_loader="$(dirname "$java_binary")/linuxoss-glibc-evaluation-loader"
install -m 0755 "$loader" "$java_loader"
"$java_loader" --library-path "$paths" "$java_binary" -cp "$work" GlibcRuntime
echo GLIBC244_PRIVATE_LOADER_FUNCTIONAL_OK_NOT_SYSTEM_REPLACEMENT
