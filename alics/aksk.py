#!/usr/bin/env python3


def load_from_file(filename):
    fp = open(filename)
    pairs = [[i.strip() for i in i.split("=")] for i in fp.readlines() if i]
    kvs = {}
    for pair in pairs:
        kvs[pair[0]] = pair[1]
    fp.close()
    return kvs["AccessKeyID"], kvs["AccessKeySecret"]