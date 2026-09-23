ARG BASE_IMAGE=docker.io/rockylinux/rockylinux@sha256:e8a49c5403b687db05d4d67333fa45808fbe74f36e683cec7abb1f7d0f2338c6
FROM ${BASE_IMAGE}

# EL8 build environment. Runtime validation must separately use RHEL/UBI 8.
# Rocky repositories are used inside this builder only, never on the target host.
RUN dnf -y --enablerepo=powertools \
      --setopt=install_weak_deps=False install \
      rpm-build rpm-sign redhat-rpm-config dnf-plugins-core make gcc gcc-c++ binutils \
      bison flex perl python3 python3.11 tar gzip bzip2 xz patch diffutils \
      findutils which file git curl gnupg2 cpio hostname \
      glibc-devel glibc-headers libstdc++-devel gmp-devel mpfr-devel \
      libmpc-devel zlib-devel openssl-devel elfutils-libelf-devel \
      libacl-devel libattr-devel libzstd-devel lz4-devel \
      texinfo gettext autoconf automake libtool ncurses-devel \
    && dnf clean all

RUN dnf -y --enablerepo=powertools --setopt=install_weak_deps=False install libidn2-devel acl attr \
      dejagnu expect perl-Text-Template perl-Test-Simple cmake elfutils-devel bc kmod \
    && dnf clean all

RUN useradd --uid 1000 --create-home builder \
    && mkdir -p /work /output \
    && chown builder:builder /work /output
USER builder
WORKDIR /work
ENV LC_ALL=C.UTF-8 LANG=C.UTF-8
CMD ["bash"]
