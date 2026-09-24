%global __provides_exclude_from ^/opt/linux-oss/jdk8/.*$
%global __requires_exclude ^lib(awt|awt_xawt|java|jli|jvm|net|nio|verify)\.so
Name: linuxoss-jdk8
Version: 1.8.0.504
Release: 1.linuxoss%{?dist}
Summary: linuxoss-jdk8 upstream EL8 evaluation build
License: GPLv2 with exceptions
URL: https://github.com/adoptium/temurin8-binaries
Source0: OpenJDK8U-jdk-sources_8u504b01.tar.gz
BuildRequires: gcc, gcc-c++, make, java-1.8.0-openjdk-devel, zip, unzip, alsa-lib-devel, cups-devel, libX11-devel, libXext-devel, libXi-devel, libXrender-devel, libXtst-devel
Vendor: Linux OSS local build

%description
Upstream build for isolated EL8 compatibility testing. Production compatibility
and all-CVE remediation are not implied by successful compilation.

%global debug_package %{nil}
%global __brp_mangle_shebangs %{nil}
%prep
%setup -q -n jdk8u504-b01-src
%build
bash configure --with-boot-jdk=/usr/lib/jvm/java-1.8.0-openjdk --with-debug-level=release --with-jvm-variants=server --with-native-debug-symbols=none --with-extra-cflags=-fcommon --with-extra-cxxflags=-fcommon --with-update-version=504 --with-build-number=b01 CC=/usr/bin/gcc CXX=/usr/bin/g++
make JOBS=2 images
%install
mkdir -p %{buildroot}/opt/linux-oss/jdk8
cp -a build/linux-x86_64-normal-server-release/images/j2sdk-image/. %{buildroot}/opt/linux-oss/jdk8/
%check
# Compile and execute using the produced JDK; JTReg is not included in this source archive.
jdk="$PWD/build/linux-x86_64-normal-server-release/images/j2sdk-image"
cat > JdkSmoke.java <<'EOF'
import javax.crypto.Cipher;
import java.security.MessageDigest;
import java.util.zip.Deflater;
public class JdkSmoke {
  public static void main(String[] args) throws Exception {
    if (!System.getProperty("java.version").startsWith("1.8.0_504")) throw new AssertionError();
    if (MessageDigest.getInstance("SHA-256").digest(new byte[3]).length != 32) throw new AssertionError();
    Cipher.getInstance("AES/GCM/NoPadding");
    new Deflater().end();
    javax.net.ssl.SSLContext.getDefault();
    System.out.println("JDK8 compile crypto TLS ZIP smoke passed");
  }
}
EOF
"$jdk/bin/javac" JdkSmoke.java
"$jdk/bin/java" -cp . JdkSmoke
%files
%license LICENSE ASSEMBLY_EXCEPTION THIRD_PARTY_README
/opt/linux-oss/jdk8/
