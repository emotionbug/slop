#!/usr/bin/env bash
set -euo pipefail
[[ -e /run/.containerenv || -e /.dockerenv ]] || { echo 'Disposable container required' >&2; exit 2; }
dnf -y --disableplugin=subscription-manager --disablerepo='*' \
  --setopt=localpkg_gpgcheck=False install /rpms/openssl4/linuxoss-openssl4-4.0.2-1.linuxoss.el8.x86_64.rpm
dnf --disableplugin=subscription-manager --disablerepo='*' check
ossl=/opt/linux-oss/openssl-4.0.2/bin/openssl
"$ossl" version -a
ldd "$ossl"
testdir=$(mktemp -d)
cd "$testdir"
"$ossl" req -x509 -newkey rsa:2048 -noenc -keyout key.pem -out cert.pem \
  -days 1 -subj '/CN=localhost' -addext 'subjectAltName=DNS:localhost' >/dev/null 2>&1
printf 'openssl4-integrity-check\n' > payload
"$ossl" dgst -sha256 -sign key.pem -out signature payload
"$ossl" pkey -in key.pem -pubout -out public.pem
"$ossl" dgst -sha256 -verify public.pem -signature signature payload
"$ossl" s_server -accept 127.0.0.1:18443 -cert cert.pem -key key.pem -www >server.log 2>&1 &
server_pid=$!
trap 'kill "$server_pid" 2>/dev/null || true' EXIT
for ((attempt=0; attempt<50; attempt++)); do
  if (echo > /dev/tcp/127.0.0.1/18443) 2>/dev/null; then break; fi
  sleep 0.1
done
printf 'GET / HTTP/1.0\r\n\r\n' | "$ossl" s_client -connect 127.0.0.1:18443 \
  -servername localhost -verify_hostname localhost -verify_return_error -CAfile cert.pem \
  -tls1_3 -quiet > response.txt 2> client.log
grep -q 'HTTP/1.0 200' response.txt
cat client.log
echo 'OPENSSL4_UBI_INSTALL_SIGN_VERIFY_TLS13_OK'
