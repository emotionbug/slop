FROM localhost/linuxoss-next-wave-installed:el8
USER 0
RUN dnf -y --disableplugin=subscription-manager --enablerepo=fixture-baseos,fixture-appstream,fixture-powertools --setopt=install_weak_deps=False install gcc-c++ libbpf libbpf-devel libxslt libxslt-devel libtiff-devel libidn-devel libevent-devel graphviz-devel gtk2-devel gdk-pixbuf2-devel openjpeg2-devel xorg-x11-server-Xvfb xorg-x11-xauth && dnf clean all
COPY compat-consumer.c /tmp/compat-consumer.c
RUN gcc -O2 -g -o /usr/local/bin/linuxoss-old-abi-consumer /tmp/compat-consumer.c $(pkg-config --cflags --libs libevent libidn libtiff-4 libbpf libxslt libgvc gdk-pixbuf-2.0 gtk+-2.0) && xvfb-run -a /usr/local/bin/linuxoss-old-abi-consumer
