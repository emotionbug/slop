/* Disposable QEMU guest only: hold an NFQUEUE bridge packet during deletion. */
#include <arpa/inet.h>
#include <errno.h>
#include <linux/netfilter.h>
#include <libnetfilter_queue/libnetfilter_queue.h>
#include <poll.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

static uint32_t packet_id;
static int queued;
static int callback(struct nfq_q_handle *q, struct nfgenmsg *msg,
                    struct nfq_data *data, void *opaque)
{
    struct nfqnl_msg_packet_hdr *h = nfq_get_msg_packet_hdr(data);
    (void)q; (void)msg; (void)opaque;
    if (!h) return -1;
    packet_id = ntohl(h->packet_id);
    queued++;
    printf("NFQUEUE_PACKET_HELD %u\n", packet_id);
    fflush(stdout);
    return 0; /* Deliberately wait to issue a verdict until bridge teardown. */
}

int main(void)
{
    char cmdline[4096] = {0}, buffer[65536];
    FILE *f = fopen("/proc/cmdline", "r");
    if (!f || !fgets(cmdline, sizeof(cmdline), f)) return 2;
    fclose(f);
    if (!strstr(cmdline, "linuxoss.nfqueue_fixture=1")) return 2;
    struct nfq_handle *h = nfq_open();
    if (!h) return 3;
    struct nfq_q_handle *q = nfq_create_queue(h, 0, callback, NULL);
    if (!q || nfq_set_mode(q, NFQNL_COPY_PACKET, 65535) < 0) return 4;
    if (system("/usr/sbin/ip netns exec sender ping -c 1 -W 4 10.99.0.1 >/tmp/ping.log 2>&1 &") != 0) return 5;
    struct pollfd p = { .fd = nfq_fd(h), .events = POLLIN };
    for (int i = 0; i < 5 && !queued; i++) {
        if (poll(&p, 1, 1000) > 0) {
            int n = recv(p.fd, buffer, sizeof(buffer), 0);
            if (n <= 0 || nfq_handle_packet(h, buffer, n) < 0) return 6;
        }
    }
    if (!queued) { fputs("No bridge packet reached queue\n", stderr); return 7; }
    if (system("/usr/sbin/ip link del br0") != 0) return 8;
    /* NETDEV_DOWN must flush the saved skb->dev entry. A late verdict must
       not access a freed bridge master. No packet is sent outside the guest. */
    if (nfq_set_verdict(q, packet_id, NF_ACCEPT, 0, NULL) < 0) return 9;
    nfq_destroy_queue(q);
    nfq_close(h);
    puts("NFQUEUE_BRIDGE_DELETE_LATE_VERDICT_PASSED");
    return 0;
}
