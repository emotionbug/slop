#!/usr/bin/env python3
"""Build a reviewable EL8 .168 patch that preserves the public NFQUEUE layout.

The CVE-2026-52912 saved-device reference remains in private allocation tail
space, after (not before) the old route-key area. Existing e->size clones copy
that space. This is a source candidate, not a runtime compatibility approval.
"""
import argparse
import difflib
from pathlib import Path


def replace_once(text, before, after):
    if text.count(before) != 1:
        raise ValueError('Expected exactly one source match: ' + before)
    return text.replace(before, after, 1)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    paths = ['include/net/netfilter/nf_queue.h', 'net/netfilter/nf_queue.c', 'net/netfilter/nfnetlink_queue.c']
    originals = {name: (args.source / name).read_text() for name in paths}
    h = originals[paths[0]]
    h = replace_once(h, '\tstruct net_device\t*skb_dev;\n', '')
    anchor = '#define nf_queue_entry_reroute(x) ((void *)x + sizeof(struct nf_queue_entry))\n'
    h = replace_once(h, anchor, anchor + '''
/* Keep the EL8 public entry layout and the route-key offset unchanged.
 * __nf_queue allocates an aligned pointer after the route keys; e->size
 * includes it, so nf_queue_entry_dup also copies the held device pointer.
 */
static inline struct net_device **nf_queue_entry_skb_dev_ptr(struct nf_queue_entry *entry)
{
\treturn (struct net_device **)((char *)entry + entry->size - sizeof(struct net_device *));
}

static inline struct net_device *nf_queue_entry_skb_dev(struct nf_queue_entry *entry)
{
\treturn *nf_queue_entry_skb_dev_ptr(entry);
}
''')
    q = originals[paths[1]]
    q = q.replace('entry->skb_dev', 'nf_queue_entry_skb_dev(entry)')
    q = replace_once(q, '\tunsigned int route_key_size;\n', '\tunsigned int route_key_size, entry_size;\n')
    q = replace_once(q, '\tentry = kmalloc(sizeof(*entry) + route_key_size, GFP_ATOMIC);',
                    '\tentry_size = ALIGN(sizeof(*entry) + route_key_size, __alignof__(struct net_device *))\n'
                    '\t\t     + sizeof(struct net_device *);\n'
                    '\tentry = kmalloc(entry_size, GFP_ATOMIC);')
    q = replace_once(q, '\t\t.skb_dev = skb->dev,\n', '')
    q = replace_once(q, '\t\t.size\t= sizeof(*entry) + route_key_size,', '\t\t.size\t= entry_size,')
    q = replace_once(q, '\t__nf_queue_entry_init_physdevs(entry);',
                    '\t*nf_queue_entry_skb_dev_ptr(entry) = skb->dev;\n\t__nf_queue_entry_init_physdevs(entry);')
    n = originals[paths[2]]
    n = replace_once(n, '\tif (entry->skb_dev && entry->skb_dev->ifindex == ifindex)',
                    '\tif (nf_queue_entry_skb_dev(entry) && nf_queue_entry_skb_dev(entry)->ifindex == ifindex)')
    modified = dict(zip(paths, [h, q, n]))
    patch = ''.join(''.join(difflib.unified_diff(originals[name].splitlines(True), modified[name].splitlines(True),
                                               fromfile='a/' + name, tofile='b/' + name)) for name in paths)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(patch, encoding='utf-8')


if __name__ == '__main__':
    main()
