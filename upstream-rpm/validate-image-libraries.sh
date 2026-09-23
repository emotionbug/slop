#!/usr/bin/env bash
set -euo pipefail
[[ -e /run/.containerenv || -e /.dockerenv ]] || { echo 'Container required' >&2; exit 2; }
profile=${1:-all}
[[ $profile == all || $profile == png-lcms ]] || exit 2
for package in libpng libjpeg-turbo lcms2; do rpm -q "$package"; done
python3 /recipe/check-elf-exports.py snapshot /tmp/image-elf-before.json \
  /usr/lib64/libpng16.so.16 /usr/lib64/libjpeg.so.62 /usr/lib64/liblcms2.so.2
# UBI has lcms2 runtime but no lcms2-devel. Read only the public header from
# the pinned source, then link to the OLD runtime and keep that test binary.
python3 - <<'PY'
import hashlib,json,pathlib,tarfile
name='lcms2-2.19.1.tar.gz'
lock=json.load(open('/recipe/sources.lock.json'))
source=next(s for s in lock['sources'] if s['name']==name)
path=pathlib.Path('/recipe/sources')/name
assert hashlib.sha256(path.read_bytes()).hexdigest()==source['sha256']
with tarfile.open(str(path)) as archive:
    pathlib.Path('/tmp/lcms2.h').write_bytes(archive.extractfile('lcms2-2.19.1/include/lcms2.h').read())
PY
cat > /tmp/image-check.c <<'C'
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <png.h>
#include <jpeglib.h>
#include "lcms2.h"
int main(void) {
  unsigned char pixels[16]={230,50,70,255,20,220,90,128,10,40,240,64,255,255,255,0};
  unsigned char restored[16];
  png_image im; memset(&im,0,sizeof(im)); im.version=PNG_IMAGE_VERSION;
  im.width=2; im.height=2; im.format=PNG_FORMAT_RGBA;
  png_alloc_size_t size=0;
  if(!png_image_write_to_memory(&im,NULL,&size,0,pixels,0,NULL))return 1;
  void *buf=malloc(size); if(!buf)return 2;
  if(!png_image_write_to_memory(&im,buf,&size,0,pixels,0,NULL))return 3;
  memset(&im,0,sizeof(im)); im.version=PNG_IMAGE_VERSION;
  if(!png_image_begin_read_from_memory(&im,buf,size))return 4;
  im.format=PNG_FORMAT_RGBA;
  if(im.width!=2 || im.height!=2 || !png_image_finish_read(&im,NULL,restored,0,NULL))return 5;
  if(memcmp(pixels,restored,sizeof(pixels)))return 6;
  png_image_free(&im); free(buf);
  memset(&im,0,sizeof(im)); im.version=PNG_IMAGE_VERSION;
  if(png_image_begin_read_from_memory(&im,"not a png",9))return 7;
  png_image_free(&im);
  struct jpeg_compress_struct enc; struct jpeg_error_mgr error;
  enc.err=jpeg_std_error(&error); jpeg_create_compress(&enc);
  unsigned char *jpeg=NULL; unsigned long jpeg_size=0;
  jpeg_mem_dest(&enc,&jpeg,&jpeg_size);
  enc.image_width=2; enc.image_height=2; enc.input_components=3; enc.in_color_space=JCS_RGB;
  jpeg_set_defaults(&enc); jpeg_set_quality(&enc,100,TRUE); jpeg_start_compress(&enc,TRUE);
  unsigned char row[6]={128,64,32,128,64,32}; JSAMPROW line=row;
  while(enc.next_scanline<enc.image_height)jpeg_write_scanlines(&enc,&line,1);
  jpeg_finish_compress(&enc); jpeg_destroy_compress(&enc);
  struct jpeg_decompress_struct dec; dec.err=jpeg_std_error(&error); jpeg_create_decompress(&dec);
  jpeg_mem_src(&dec,jpeg,jpeg_size); if(jpeg_read_header(&dec,TRUE)!=JPEG_HEADER_OK)return 8;
  jpeg_start_decompress(&dec);
  if(dec.output_width!=2 || dec.output_height!=2 || dec.output_components!=3)return 9;
  unsigned char decoded[6]; JSAMPROW out=decoded;
  while(dec.output_scanline<dec.output_height){
    jpeg_read_scanlines(&dec,&out,1);
    for(int i=0;i<6;i++)if(abs((int)decoded[i]-row[i])>3)return 10;
  }
  jpeg_finish_decompress(&dec); jpeg_destroy_decompress(&dec); free(jpeg);
  cmsHPROFILE rgb=cmsCreate_sRGBProfile(), xyz=cmsCreateXYZProfile();
  if(!rgb || !xyz)return 11;
  cmsHTRANSFORM forward=cmsCreateTransform(rgb,TYPE_RGB_DBL,xyz,TYPE_XYZ_DBL,INTENT_RELATIVE_COLORIMETRIC,0);
  cmsHTRANSFORM reverse=cmsCreateTransform(xyz,TYPE_XYZ_DBL,rgb,TYPE_RGB_DBL,INTENT_RELATIVE_COLORIMETRIC,0);
  if(!forward || !reverse)return 12;
  double a[3]={0.6,0.3,0.1},b[3],c[3];
  cmsDoTransform(forward,a,b,1);cmsDoTransform(reverse,b,c,1);
  for(int i=0;i<3;i++)if(!isfinite(c[i]) || fabs(a[i]-c[i])>0.005)return 13;
  cmsDeleteTransform(forward);cmsDeleteTransform(reverse);cmsCloseProfile(rgb);cmsCloseProfile(xyz);
  printf("IMAGE_ROUNDTRIPS_OK png=%s lcms=%u\n",png_get_libpng_ver(NULL),cmsGetEncodedCMMversion());
  return 0;
}
C
gcc -O2 -I/tmp /tmp/image-check.c -lpng16 -ljpeg -l:liblcms2.so.2 -lm -o /tmp/image-check
/tmp/image-check
rpms=(
  /rpms/libpng/libpng-1.6.58-1.linuxoss.el8.x86_64.rpm
  /rpms/libpng/libpng-devel-1.6.58-1.linuxoss.el8.x86_64.rpm
  /rpms/lcms2/lcms2-2.19.1-1.linuxoss.el8.x86_64.rpm
)
if [[ $profile == all ]]; then
  rpms+=(/rpms/libjpeg-turbo/libjpeg-turbo-3.2.0-1.linuxoss.el8.x86_64.rpm
    /rpms/libjpeg-turbo/libjpeg-turbo-devel-3.2.0-1.linuxoss.el8.x86_64.rpm)
fi
dnf -y --disableplugin=subscription-manager --disablerepo='*' \
  --setopt=localpkg_gpgcheck=False install "${rpms[@]}"
dnf --disableplugin=subscription-manager --disablerepo='*' check
abi_status=0
python3 /recipe/check-elf-exports.py compare /tmp/image-elf-before.json || abi_status=$?
/tmp/image-check
ldd /tmp/image-check
if [[ $abi_status != 0 ]]; then
  echo 'IMAGE_FUNCTIONAL_CHECKS_PASSED_BUT_ABI_EXPORTS_FAILED; candidate remains held'
  exit "$abi_status"
fi
echo "UBI_IMAGE_LIBRARY_UPGRADE_OLD_BINARY_ROUNDTRIPS_OK profile=$profile"
