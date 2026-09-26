#!/bin/bash
set -Eeuo pipefail
test -f /run/.containerenv
label=${1:?test label}
[[ $label =~ ^[a-z0-9-]+$ ]]
work=$(mktemp -d /tmp/linuxoss-backport-runtime-XXXXXX)
tls_pid=
ssh_pid=
trap '[[ -z "$tls_pid" ]] || kill "$tls_pid" 2>/dev/null || :; [[ -z "$ssh_pid" ]] || kill "$ssh_pid" 2>/dev/null || :' EXIT
exec > >(tee "/out/$label-runtime.log") 2>&1
rpm -V openssl openssl-libs openssl-devel
dnf --noplugins --disablerepo='*' check
openssl version -a
nm -D --defined-only /usr/lib64/libcrypto.so.1.1 > "/out/$label-crypto-exports.txt"
nm -D --defined-only /usr/lib64/libssl.so.1.1 > "/out/$label-ssl-exports.txt"
/usr/libexec/platform-python - "$label" <<'PY'
import json, pathlib, ssl, sys
root = pathlib.Path('/out')
def symbols(p):
    return {tuple(line.split()[-2:]) for line in p.read_text().splitlines() if len(line.split()) >= 3}
result = {}
for lib in ('crypto', 'ssl'):
    old = symbols(root / ('openssl-' + lib + '-exports-before.txt'))
    new = symbols(root / (sys.argv[1] + '-' + lib + '-exports.txt'))
    result[lib] = {'old_count': len(old), 'new_count': len(new), 'removed_or_type_changed': sorted(old - new)}
    assert not old - new, result
(root / (sys.argv[1] + '-abi.json')).write_text(json.dumps(result, indent=2) + '\n')
print('PUBLIC_SYMBOL_ABI_PASSED', ssl.OPENSSL_VERSION)
PY
openssl req -x509 -newkey rsa:2048 -nodes -days 1 -subj /CN=localhost \
  -addext subjectAltName=DNS:localhost,IP:127.0.0.1 \
  -keyout "$work/tls.key" -out "$work/tls.crt" > "$work/keygen.log" 2>&1
cat > "$work/tls-server.py" <<'PY'
import http.server, ssl, sys
class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        data = b'BACKPORT_HTTPS_OK\n'
        self.send_response(200)
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)
    def finish(self):
        super().finish()
        try:
            self.connection.settimeout(2)
            self.connection.unwrap().close()
        except (OSError, ssl.SSLError):
            pass
server = http.server.HTTPServer(('127.0.0.1', 14443), Handler)
ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ctx.load_cert_chain(sys.argv[1], sys.argv[2])
server.socket = ctx.wrap_socket(server.socket, server_side=True)
server.serve_forever()
PY
/usr/libexec/platform-python "$work/tls-server.py" "$work/tls.crt" "$work/tls.key" \
  > "$work/tls-server.log" 2>&1 &
tls_pid=$!
sleep 1
for protocol in tls1_2 tls1_3; do
  printf 'GET / HTTP/1.0\r\n\r\n' | timeout 10 openssl s_client -connect 127.0.0.1:14443 \
    -servername localhost -verify_return_error -CAfile "$work/tls.crt" -"$protocol" \
    > "$work/$protocol.log" 2>&1
  grep -q 'Verify return code: 0 (ok)' "$work/$protocol.log"
  echo "TLS_PASSED $protocol"
done
curl --fail --silent --show-error --cacert "$work/tls.crt" https://localhost:14443/ > "$work/curl.html"
grep -q 'BACKPORT_HTTPS_OK' "$work/curl.html"
/usr/libexec/platform-python - "$work/tls.crt" <<'PY'
import socket, ssl, sys
ctx = ssl.create_default_context(cafile=sys.argv[1])
with socket.create_connection(('127.0.0.1', 14443)) as raw:
    with ctx.wrap_socket(raw, server_hostname='localhost') as s:
        s.sendall(b'GET / HTTP/1.0\r\n\r\n')
        assert b'HTTP/1.0 200 OK' in s.recv(8192)
        print('PLATFORM_PYTHON_TLS_PASSED', s.version())
PY
ssh-keygen -q -t ed25519 -N '' -f "$work/hostkey"
ssh-keygen -q -t ed25519 -N '' -f "$work/clientkey"
id linuxoss-fixture >/dev/null 2>&1 || useradd -M -s /bin/sh -p x linuxoss-fixture
mkdir -p /home/linuxoss-fixture
chown linuxoss-fixture:linuxoss-fixture /home/linuxoss-fixture
chmod 755 "$work"
cp "$work/clientkey.pub" "$work/authorized_keys"
cat > "$work/sshd_config" <<EOF
ListenAddress 127.0.0.1
Port 12222
HostKey $work/hostkey
PidFile $work/sshd.pid
AuthorizedKeysFile $work/authorized_keys
StrictModes no
PasswordAuthentication no
ChallengeResponseAuthentication no
UsePAM yes
UseDNS no
AllowUsers linuxoss-fixture
EOF
/usr/sbin/sshd -t -f "$work/sshd_config"
/usr/sbin/sshd -D -e -f "$work/sshd_config" > "$work/sshd.log" 2>&1 &
ssh_pid=$!
sleep 1
ssh -F /dev/null -p 12222 -i "$work/clientkey" -o IdentitiesOnly=yes -o BatchMode=yes \
  -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile="$work/known_hosts" \
  linuxoss-fixture@127.0.0.1 'printf SSH_BACKPORT_RUNTIME_PASSED' > "$work/ssh-result.txt"
grep -qx SSH_BACKPORT_RUNTIME_PASSED "$work/ssh-result.txt"
cat "$work/ssh-result.txt"
echo
echo BACKPORT_RUNTIME_PASSED
