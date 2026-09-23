#include "onigposix-6.8.2.h"
#include <stdio.h>
#include <string.h>
int main(void) {
  regex_t re;
  regmatch_t matches[3];
  char error[256];
  int code=regcomp(&re,"^([a-z]+)=([0-9]+)$",REG_EXTENDED);
  if(code)return 1;
  if(regexec(&re,"name=123",3,matches,0))return 2;
  if(matches[1].rm_so!=0||matches[1].rm_eo!=4||matches[2].rm_so!=5||matches[2].rm_eo!=8)return 3;
  if(regexec(&re,"not a pair",3,matches,0)!=REG_NOMATCH)return 4;
  regfree(&re);
  code=regcomp(&re,"[",REG_EXTENDED);
  if(!code||!regerror(code,&re,error,sizeof(error)))return 5;
  puts("ONIG_EL8_POSIX_OLD_BINARY_OK");return 0;
}
