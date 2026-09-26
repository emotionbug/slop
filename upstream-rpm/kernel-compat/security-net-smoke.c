#define _GNU_SOURCE
#include <arpa/inet.h>
#include <errno.h>
#include <fcntl.h>
#include <netinet/in.h>
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/wait.h>
#include <unistd.h>

static void die(const char *msg) { perror(msg); exit(1); }
static int sock(int type) {
    int fd = socket(AF_INET, type, 0); if (fd < 0) die("socket");
    struct timeval tv = {5, 0};
    if (setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv))) die("timeout");
    return fd;
}
static void exchange(int fd) {
    char buf[32];
    if (send(fd, "linuxoss-smoke", 13, 0) != 13) die("send");
    if (recv(fd, buf, sizeof(buf), 0) != 13 || memcmp(buf,"linuxoss-smoke",13)) die("reply");
}
int main(void) {
    alarm(20);
    struct sockaddr_in addr = {.sin_family=AF_INET,.sin_port=htons(18080)};
    inet_pton(AF_INET,"10.99.1.1",&addr.sin_addr);
    int tcp=sock(SOCK_STREAM), udp=sock(SOCK_DGRAM);
    if (bind(tcp,(void*)&addr,sizeof(addr)) || listen(tcp,1)) die("listen");
    if (bind(udp,(void*)&addr,sizeof(addr))) die("udp bind");
    pid_t child=fork(); if(child<0) die("fork");
    if(!child) {
        close(tcp); close(udp);
        int ns=open("/run/netns/sender",O_RDONLY); if(ns<0||setns(ns,CLONE_NEWNET)) die("setns");
        close(ns);
        int c=sock(SOCK_STREAM);
        if(connect(c,(void*)&addr,sizeof(addr))) die("tcp connect");
        exchange(c); close(c);
        c=sock(SOCK_DGRAM);
        if(connect(c,(void*)&addr,sizeof(addr))) die("udp connect");
        exchange(c); close(c);
        _exit(0);
    }
    int c=accept(tcp,NULL,NULL); if(c<0) die("accept");
    char buf[32]; ssize_t n=recv(c,buf,sizeof(buf),0);
    if(n!=13||memcmp(buf,"linuxoss-smoke",13)||send(c,buf,n,0)!=n) die("tcp echo");
    close(c); close(tcp);
    struct sockaddr_in peer; socklen_t plen=sizeof(peer);
    n=recvfrom(udp,buf,sizeof(buf),0,(void*)&peer,&plen);
    if(n!=13||memcmp(buf,"linuxoss-smoke",13)||sendto(udp,buf,n,0,(void*)&peer,plen)!=n) die("udp echo");
    close(udp);
    int status;
    if(waitpid(child,&status,0)!=child||!WIFEXITED(status)||WEXITSTATUS(status)) die("child");
    puts("SERVER_MODULE_TCP_UDP_CROSS_NAMESPACE_PASSED");
    return 0;
}
