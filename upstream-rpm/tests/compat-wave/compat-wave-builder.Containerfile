FROM localhost/linuxoss-next-wave-gdb-builder:el8
USER 0
RUN dnf -y install epel-release
RUN dnf -y --enablerepo=powertools --setopt=install_weak_deps=False install ninja-build libjpeg-turbo-devel libtiff-devel libpng-devel lcms2-devel gdk-pixbuf2-devel atk-devel pango-devel libX11-devel libXext-devel libXrender-devel libXi-devel libXrandr-devel libXcursor-devel libXcomposite-devel libXdamage-devel cairo-devel cups-devel xorg-x11-server-Xvfb xorg-x11-xauth openbox gd-devel jansson-devel libcap-devel && dnf clean all
RUN dnf -y --enablerepo=powertools install python3.11-pip libtool-ltdl-devel libabigail help2man elfutils-libelf-devel jbigkit-devel gdk-pixbuf2-modules && dnf clean all && python3.11 -m pip install --no-cache-dir meson==1.9.1
ENV CC=/usr/bin/gcc CXX=/usr/bin/g++ LD_LIBRARY_PATH= PKG_CONFIG_PATH= PATH=/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin
USER builder
