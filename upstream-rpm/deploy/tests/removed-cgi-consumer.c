/* A surviving external user of a retired libcups CGI export must block upgrade. */
extern int cgiGetSize(const char *name);
int linuxoss_fixture(void) { return cgiGetSize("fixture"); }
