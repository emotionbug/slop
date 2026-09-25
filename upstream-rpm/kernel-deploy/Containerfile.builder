FROM localhost/linuxoss-compat-wave-builder:el8
USER root
COPY dwarves.rpm /tmp/kernel-dwarves.rpm
COPY binutils.rpm /tmp/kernel-binutils.rpm
RUN dnf -y --enablerepo=powertools --setopt=install_weak_deps=False install bc rsync kmod git ncurses-devel perl perl-Data-Dumper elfutils-devel \
    && dnf -y --disablerepo='*' install /tmp/kernel-dwarves.rpm /tmp/kernel-binutils.rpm \
    && rm /tmp/kernel-dwarves.rpm /tmp/kernel-binutils.rpm && dnf clean all
USER builder
