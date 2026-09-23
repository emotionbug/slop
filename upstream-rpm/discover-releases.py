#!/usr/bin/env python3
"""Collect release candidates from primary sources, never auto-promote to build pins."""
import concurrent.futures
import datetime
import json
import pathlib
import re
import shutil
import subprocess
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
GITHUB = {
    'avahi':'avahi/avahi', 'c-ares':'c-ares/c-ares', 'cronie':'cronie-crond/cronie',
    'cups':'OpenPrinting/cups', 'curl':'curl/curl',
    'device-mapper-persistent-data':'jthornber/thin-provisioning-tools',
    'efivar':'rhboot/efivar', 'expat':'libexpat/libexpat',
    'firewalld':'firewalld/firewalld', 'flex':'westes/flex', 'fwupd':'fwupd/fwupd',
    'gd':'libgd/libgd', 'ghostscript':'ArtifexSoftware/ghostpdl-downloads',
    'glusterfs':'gluster/glusterfs', 'harfbuzz':'harfbuzz/harfbuzz',
    'icu':'unicode-org/icu', 'iputils':'iputils/iputils',
    'iscsi-initiator-utils':'open-iscsi/open-iscsi', 'jasper':'jasper-software/jasper',
    'jq':'jqlang/jq', 'kbd':'legionus/kbd', 'lcms2':'mm2/Little-CMS',
    'libbpf':'libbpf/libbpf', 'libarchive':'libarchive/libarchive',
    'libevent':'libevent/libevent', 'libjpeg-turbo':'libjpeg-turbo/libjpeg-turbo',
    'libpcap':'the-tcpdump-group/libpcap', 'libpng':'pnggroup/libpng',
    'libsolv':'openSUSE/libsolv', 'libstoragemgmt':'libstorage/libstoragemgmt',
    'microcode_ctl':'intel/Intel-Linux-Processor-Microcode-Data-Files',
    'mtr':'traviscross/mtr', 'oniguruma':'kkos/oniguruma',
    'open-vm-tools':'vmware/open-vm-tools', 'openjpeg2':'uclouvain/openjpeg',
    'pam':'linux-pam/linux-pam', 'pcre2':'PCRE2Project/pcre2',
    'popt':'rpm-software-management/popt', 'protobuf-c':'protobuf-c/protobuf-c',
    'python-pip':'pypa/pip', 'rpm':'rpm-software-management/rpm',
    'rsyslog':'rsyslog/rsyslog', 'shadow-utils':'shadow-maint/shadow',
    'shim':'rhboot/shim', 'sos':'sosreport/sos', 'sssd':'SSSD/sssd',
    'sysstat':'sysstat/sysstat', 'systemd':'systemd/systemd',
    'tcpdump':'the-tcpdump-group/tcpdump', 'tmux':'tmux/tmux',
    'vim':'vim/vim', 'xz':'tukaani-project/xz', 'zlib':'madler/zlib',
    'zstd':'facebook/zstd',
}
GNU = ['binutils','bison','coreutils','cpio','diffutils','emacs','gawk','gdb',
       'glibc','grub','libidn','libtasn1','nano','patch','sed','tar','time','wget']
DIRECTORIES = {
    'bind':('https://downloads.isc.org/isc/bind9/','bind-'),
    'bzip2':('https://sourceware.org/pub/bzip2/','bzip2'),
    'cairo':('https://cairographics.org/releases/','cairo'),
    'cifs-utils':('https://download.samba.org/pub/linux-cifs/cifs-utils/','cifs-utils'),
    'dbus':('https://dbus.freedesktop.org/releases/dbus/','dbus'),
    'elfutils':('https://sourceware.org/elfutils/ftp/','elfutils'),
    'file':('https://astron.com/pub/file/','file'),
    'gnupg2':('https://gnupg.org/ftp/gcrypt/gnupg/','gnupg'),
    'libgcrypt':('https://gnupg.org/ftp/gcrypt/libgcrypt/','libgcrypt'),
    'libXpm':('https://www.x.org/releases/individual/lib/','libXpm'),
    'libpcap':('https://www.tcpdump.org/release/','libpcap'),
    'libtheora':('https://downloads.xiph.org/releases/theora/','libtheora'),
    'libtiff':('https://download.osgeo.org/libtiff/','tiff'),
    'lvm2':('https://sourceware.org/pub/lvm2/','LVM2'),
    'mdadm':('https://www.kernel.org/pub/linux/utils/raid/mdadm/','mdadm'),
    'ncurses':('https://ftp.gnu.org/gnu/ncurses/','ncurses'),
    'openldap':('https://www.openldap.org/software/download/OpenLDAP/openldap-release/','openldap'),
    'openssh':('https://cdn.openbsd.org/pub/OpenBSD/OpenSSH/portable/','openssh'),
    'perl':('https://www.cpan.org/src/5.0/','perl'),
    'samba':('https://download.samba.org/pub/samba/stable/','samba'),
    'sysstat':('https://sysstat.github.io/files/','sysstat'),
    'tcpdump':('https://www.tcpdump.org/release/','tcpdump'),
    'xdg-utils':('https://www.freedesktop.org/releases/xdg-utils/','xdg-utils'),
}
GNOME = {'NetworkManager':'NetworkManager','gdk-pixbuf2':'gdk-pixbuf',
         'glib-networking':'glib-networking','glib2':'glib','gtk2':'gtk',
         'librsvg2':'librsvg','libsoup':'libsoup','libxml2':'libxml2','libxslt':'libxslt'}


def collect(item):
    project, kind, url, archive = item
    result = {'source_project':project, 'url':url, 'kind':kind,
              'status':'candidate-needs-review', 'version_or_tag':None}
    try:
        if kind == 'github-project-latest-release' and shutil.which('gh'):
            # Public metadata only. The CLI handles existing credentials;
            # tokens are never read, printed, or written to the report.
            result_api = subprocess.run(['gh','api',url.removeprefix('https://api.github.com/')],
                check=True, capture_output=True, text=True, timeout=30)
            body = result_api.stdout
        else:
            req = urllib.request.Request(url, headers={'User-Agent':'linux-oss-upstream-review'})
            with urllib.request.urlopen(req, timeout=25) as response:
                body = response.read().decode('utf-8')
        if kind == 'github-project-latest-release':
            release = json.loads(body)
            if release.get('draft') or release.get('prerelease'):
                raise ValueError('Upstream latest endpoint returned a pre-release')
            result.update(version_or_tag=release['tag_name'],
                          evidence_url=release['html_url'],
                          published_at=release.get('published_at'))
        elif kind == 'gnome-release-cache':
            cache=json.loads(body)
            versions={v for v in cache[1][archive] if re.fullmatch(r'\d+(?:\.\d+)+',v)}
            if not versions:
                raise ValueError('No numeric releases in GNOME cache')
            result.update(version_or_tag=max(versions,key=lambda v:tuple(map(int,v.split('.')))),
                          evidence_url=url,note='Highest numeric source archive; may be a development branch. Stable/API branch review required.')
        else:
            versions = set(re.findall(re.escape(archive)+r'-(\d+(?:\.\d+)+(?:p\d+)?)\.tar\.(?:gz|xz|bz2)',body))
            if not versions:
                raise ValueError('No numeric release archive found')
            version = max(versions, key=lambda v:tuple(map(int,re.findall(r'\d+',v))))
            result.update(version_or_tag=version, evidence_url=url,
                          note='Highest numeric archive; maintenance branch/stable policy must be reviewed')
        result['checked_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        result.update(status='lookup-failed', error=str(exc))
    return result


def main():
    scope=json.loads((ROOT/'output/scope.json').read_text(encoding='utf-8'))
    targets={p['source_project'] for p in scope['packages']}
    jobs=[(p,'github-project-latest-release',f'https://api.github.com/repos/{repo}/releases/latest',None)
          for p,repo in GITHUB.items() if p in targets]
    jobs += [('grub2' if p=='grub' else p, 'gnu-official-release-directory',
              f'https://ftp.gnu.org/gnu/{p}/',p) for p in GNU if ('grub2' if p=='grub' else p) in targets]
    jobs += [(p,'official-release-directory',url,name) for p,(url,name) in DIRECTORIES.items() if p in targets and p not in GITHUB]
    jobs += [(p,'gnome-release-cache',f'https://download.gnome.org/sources/{name}/cache.json',name) for p,name in GNOME.items() if p in targets]
    prior_path=ROOT/'output/release-candidates.json'
    prior={r['source_project']:r for r in json.loads(prior_path.read_text(encoding='utf-8'))['results']} if prior_path.exists() else {}
    ready=[prior[j[0]] for j in jobs if j[0] in prior and prior[j[0]]['status']=='candidate-needs-review']
    jobs=[j for j in jobs if j[0] not in {r['source_project'] for r in ready}]
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        results=sorted(ready+list(executor.map(collect,jobs)),key=lambda r:r['source_project'])
    document={'checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'note':'Candidate discovery only. No release is automatically pinned, compiled, installed, or asserted to fix every CVE.',
              'results':results}
    (ROOT/'output/release-candidates.json').write_text(json.dumps(document,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'looked_up':len(results),'candidates':sum(r['status']=='candidate-needs-review' for r in results),
                      'failures':[{k:r.get(k) for k in ('source_project','error')} for r in results if r['status']=='lookup-failed']},ensure_ascii=False))


if __name__=='__main__':
    main()
