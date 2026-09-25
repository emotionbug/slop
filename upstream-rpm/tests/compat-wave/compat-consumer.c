#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include <event2/event.h>
#include <event2/buffer.h>
#include <idna.h>
#include <stringprep.h>
#include <tiffio.h>
#include <bpf/libbpf.h>
#include <bpf/btf.h>
#include <libxslt/transform.h>
#include <libxslt/xsltutils.h>
#include <graphviz/gvc.h>
#include <gtk/gtk.h>
int main(int argc,char **argv) {
 struct event_base *base=event_base_new(); assert(base); event_base_free(base);
 struct evbuffer *buf=evbuffer_new(); assert(buf); assert(evbuffer_add(buf,"abc",3)==0); char out[4]={0}; assert(evbuffer_remove(buf,out,3)==3); assert(strcmp(out,"abc")==0); evbuffer_free(buf);
 char *decoded=NULL; assert(idna_to_unicode_8z8z("xn--bcher-kva.de",&decoded,0)==0); assert(strcmp(decoded,"b\xc3\xbc" "cher.de")==0); free(decoded);
 char prep[128]="Example"; assert(stringprep(prep,sizeof(prep),0,stringprep_nameprep)==0); assert(strcmp(prep,"example")==0);
 TIFF *t=TIFFOpen("/tmp/linuxoss-abi.tif","w"); assert(t);
 assert(TIFFSetField(t,TIFFTAG_IMAGEWIDTH,1)); assert(TIFFSetField(t,TIFFTAG_IMAGELENGTH,1));
 assert(TIFFSetField(t,TIFFTAG_BITSPERSAMPLE,8)); assert(TIFFSetField(t,TIFFTAG_SAMPLESPERPIXEL,1)); assert(TIFFSetField(t,TIFFTAG_PHOTOMETRIC,PHOTOMETRIC_MINISBLACK)); assert(TIFFSetField(t,TIFFTAG_PLANARCONFIG,PLANARCONFIG_CONTIG));
 unsigned char pixel=127; assert(TIFFWriteScanline(t,&pixel,0,0)>=0); TIFFClose(t);
 t=TIFFOpen("/tmp/linuxoss-abi.tif","r"); assert(t); pixel=0; assert(TIFFReadScanline(t,&pixel,0,0)>=0); assert(pixel==127); TIFFClose(t);
 struct btf *btf=btf__new_empty(); assert(btf && !libbpf_get_error(btf)); btf__free(btf);
 const char *stylesheet="<xsl:stylesheet version='1.0' xmlns:xsl='http://www.w3.org/1999/XSL/Transform'><xsl:template match='/'><ok><xsl:value-of select='/r/v'/></ok></xsl:template></xsl:stylesheet>";
 xmlDocPtr sd=xmlReadMemory(stylesheet,strlen(stylesheet),"x",NULL,0); assert(sd); xsltStylesheetPtr ss=xsltParseStylesheetDoc(sd); assert(ss);
 xmlDocPtr doc=xmlReadMemory("<r><v>42</v></r>",16,"y",NULL,0); assert(doc); xmlDocPtr res=xsltApplyStylesheet(ss,doc,NULL); assert(res); xmlChar *xml=NULL; int len=0; assert(xsltSaveResultToString(&xml,&len,res,ss)>=0); assert(strstr((char*)xml,"42")); xmlFree(xml); xmlFreeDoc(res);xmlFreeDoc(doc);xsltFreeStylesheet(ss);
 GVC_t *gvc=gvContext(); assert(gvc); Agraph_t *graph=agmemread("digraph G {a -> b}"); assert(graph); assert(gvLayout(gvc,graph,"dot")==0); char *svg=NULL; unsigned length=0; assert(gvRenderData(gvc,graph,"svg",&svg,&length)==0); assert(strstr(svg,"<svg")); gvFreeRenderData(svg); gvFreeLayout(gvc,graph);agclose(graph);gvFreeContext(gvc);
 gtk_init(&argc,&argv); GtkWidget *label=gtk_label_new("ABI OK"); assert(strcmp(gtk_label_get_text(GTK_LABEL(label)),"ABI OK")==0); gtk_widget_destroy(label);
 GdkPixbuf *p=gdk_pixbuf_new(GDK_COLORSPACE_RGB,FALSE,8,2,2); assert(p); gdk_pixbuf_fill(p,0xff0000ff);GError *err=NULL;assert(gdk_pixbuf_save(p,"/tmp/linuxoss-abi.png","png",&err,NULL));g_object_unref(p);p=gdk_pixbuf_new_from_file("/tmp/linuxoss-abi.png",&err);assert(p&&gdk_pixbuf_get_width(p)==2);g_object_unref(p);
 puts("EL8_PRECOMPILED_CONSUMER_OK: event idn tiff bpf xslt graphviz gtk pixbuf"); return 0;
}
