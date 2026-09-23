#!/usr/bin/env bash
set -euo pipefail
[[ -e /run/.containerenv || -e /.dockerenv ]] || exit 2
dnf -y --disableplugin=subscription-manager --disablerepo='*' \
  --setopt=localpkg_gpgcheck=False install \
  /rpms/c-ares/c-ares-1.34.8-1.linuxoss.el8.x86_64.rpm \
  /rpms/c-ares/c-ares-devel-1.34.8-1.linuxoss.el8.x86_64.rpm
dnf --disableplugin=subscription-manager --disablerepo='*' check
cat > /tmp/cares-check.c <<'C'
#include <ares.h>
#include <netdb.h>
#include <stdio.h>
#include <string.h>
int main(void){
  if(ares_library_init(ARES_LIB_INIT_ALL))return 1;
  if(strcmp(ares_version(NULL),"1.34.8"))return 2;
  const unsigned char reply[]={0x12,0x34,0x81,0x80,0,1,0,1,0,0,0,0,
    7,'e','x','a','m','p','l','e',3,'c','o','m',0,0,1,0,1,
    0xc0,0x0c,0,1,0,1,0,0,0,60,0,4,192,0,2,123};
  struct hostent *host=NULL;
  if(ares_parse_a_reply(reply,sizeof(reply),&host,NULL,NULL))return 3;
  if(!host || host->h_length!=4 || memcmp(host->h_addr_list[0],reply+sizeof(reply)-4,4))return 4;
  ares_free_hostent(host);host=NULL;
  if(ares_parse_a_reply(reply,8,&host,NULL,NULL)==ARES_SUCCESS)return 5;
  ares_channel channel;
  if(ares_init(&channel)!=ARES_SUCCESS)return 6;
  ares_destroy(channel);
  ares_library_cleanup();
  puts("UBI_CARES_INSTALL_DNS_PARSER_OK");return 0;
}
C
gcc -O2 /tmp/cares-check.c -lcares -o /tmp/cares-check
/tmp/cares-check
