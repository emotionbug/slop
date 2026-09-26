/* Compile only; this object is never loaded into a kernel. */
#include <linux/module.h>
#include <linux/skbuff.h>
#include <linux/netdevice.h>
#include <linux/netfilter.h>
#include <linux/slab.h>
#include <linux/proc_fs.h>
#include <linux/sched.h>
#include <net/sock.h>
#include <net/net_namespace.h>
#include <net/netfilter/nf_queue.h>

struct sk_buff probe_skb;
struct net_device probe_netdev;
struct sock probe_sock;
struct socket probe_socket;
struct net probe_net;
struct task_struct probe_task;
struct nf_hook_ops probe_nf_hook_ops;
struct nf_hook_state probe_nf_hook_state;
struct nf_queue_entry probe_nf_queue_entry;
struct proto probe_proto;
struct proc_ops probe_proc_ops;

/* Explicit typed pointers retain DWARF for representative imported APIs. */
#define PROBE_API(sym) typeof(sym) *__gendwarfksyms_ptr_##sym __used = &sym
PROBE_API(nf_register_net_hook);
PROBE_API(nf_unregister_net_hook);
PROBE_API(skb_copy);
PROBE_API(skb_clone);
PROBE_API(dev_queue_xmit);
PROBE_API(proc_create_data);
PROBE_API(init_net);
MODULE_LICENSE("GPL");
