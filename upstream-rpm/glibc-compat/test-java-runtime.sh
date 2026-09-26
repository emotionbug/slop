#!/usr/bin/env bash
set -Eeuo pipefail
[[ -f /run/.containerenv ]]
exec > >(tee /out/java-tomcat-runtime.log) 2>&1
fixtures=/out/java-fixtures
work=$(mktemp -d /tmp/linuxoss-java-fixture-XXXXXX)
tomcat_pid=
trap '[[ -z "$tomcat_pid" ]] || kill "$tomcat_pid" 2>/dev/null || :' EXIT
tar -xzf "$fixtures/OpenJDK8U-jdk_x64_linux_hotspot_8u504b01.tar.gz" -C "$work"
tar -xzf "$fixtures/apache-tomcat-9.0.122.tar.gz" -C "$work"
export JAVA_HOME="$work/jdk8u504-b01"
export CATALINA_HOME="$work/apache-tomcat-9.0.122"
export CATALINA_BASE="$work/tomcat-base"
"$JAVA_HOME/bin/java" -version
mkdir -p "$CATALINA_BASE"/{conf,logs,temp,webapps/ROOT,work}
cp -a "$CATALINA_HOME/conf/." "$CATALINA_BASE/conf/"
sed -i -e 's/port="8005"/port="-1"/' -e 's/port="8080"/address="127.0.0.1" port="18080"/' "$CATALINA_BASE/conf/server.xml"
cat > "$work/BackportFixture.java" <<'JAVA'
import java.nio.*;
import java.nio.channels.*;
import java.nio.charset.*;
import java.nio.file.*;
import java.net.*;
import java.util.*;
import java.util.concurrent.*;
import java.util.zip.*;
import java.io.*;
public class BackportFixture {
  public static void main(String[] args) throws Exception {
    if (!InetAddress.getByName("localhost").isLoopbackAddress()) throw new AssertionError("NSS");
    String s = "한국어 일본어 mixed";
    byte[] encoded = s.getBytes("UTF-8");
    if (!s.equals(new String(encoded, "UTF-8"))) throw new AssertionError("charset");
    Path file = Files.createTempFile("linuxoss-nio", ".tmp");
    try (FileChannel c = FileChannel.open(file, StandardOpenOption.READ, StandardOpenOption.WRITE);
         FileLock lock = c.lock()) {
      c.write(ByteBuffer.wrap(encoded));
      MappedByteBuffer mapped = c.map(FileChannel.MapMode.READ_ONLY, 0, encoded.length);
      byte[] actual = new byte[encoded.length]; mapped.get(actual);
      if (!Arrays.equals(actual, encoded)) throw new AssertionError("mmap");
    }
    ExecutorService threads = Executors.newFixedThreadPool(4);
    List<Future<Integer>> tasks = new ArrayList<>();
    for (int i=0; i<100; i++) tasks.add(threads.submit(() -> encoded.length));
    for (Future<Integer> f : tasks) if (f.get()!=encoded.length) throw new AssertionError("pthread");
    threads.shutdown();
    ByteArrayOutputStream compressed = new ByteArrayOutputStream();
    try (GZIPOutputStream zip = new GZIPOutputStream(compressed)) { zip.write(encoded); }
    try (GZIPInputStream zip = new GZIPInputStream(new ByteArrayInputStream(compressed.toByteArray()))) {
      ByteArrayOutputStream plain = new ByteArrayOutputStream();
      for (int b; (b=zip.read())!=-1;) plain.write(b);
      if (!Arrays.equals(encoded, plain.toByteArray())) throw new AssertionError("zlib");
    }
    if (new ProcessBuilder("/usr/bin/getent", "hosts", "localhost").inheritIO().start().waitFor()!=0)
      throw new AssertionError("spawn");
    Files.delete(file);
    System.out.println("JAVA8_NSS_PTHREAD_MMAP_CHARSET_ZLIB_SPAWN_PASSED");
  }
}
JAVA
"$JAVA_HOME/bin/javac" -encoding UTF-8 "$work/BackportFixture.java"
"$JAVA_HOME/bin/java" -cp "$work" BackportFixture
cat > "$CATALINA_BASE/webapps/ROOT/index.jsp" <<'JSP'
<%@ page contentType="text/plain; charset=UTF-8" %><% out.print("TOMCAT_JSP_BACKPORT_PASSED:" + System.getProperty("java.version")); %>
JSP
bash "$CATALINA_HOME/bin/catalina.sh" run > "$work/tomcat.log" 2>&1 &
tomcat_pid=$!
for attempt in {1..30}; do
  if curl -fsS http://127.0.0.1:18080/index.jsp > "$work/result.txt" 2>/dev/null; then break; fi
  kill -0 "$tomcat_pid"
  sleep 1
done
cat "$work/result.txt"
grep -q 'TOMCAT_JSP_BACKPORT_PASSED:1.8.0_504' "$work/result.txt"
echo JAVA_TOMCAT_BACKPORT_RUNTIME_PASSED
