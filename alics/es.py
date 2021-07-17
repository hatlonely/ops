#!/usr/bin/env python3

import argparse
import json
import hashlib
from elasticsearch import Elasticsearch


def put_index(client: Elasticsearch, index, filename, keys):
    fp = open(filename)
    keys = [x.strip() for x in keys.split(",")]
    for line in fp:
        if not line.strip():
            continue
        obj = json.loads(line)
        if not obj:
            continue
        key = hashlib.md5("_".join([obj[x] for x in keys]).encode()).hexdigest()
        if not key:
            continue
        client.index(index=index, id=key, body=obj)
    fp.close()


def del_index(client: Elasticsearch, index):
    client.indices.delete(index=index)


def main():
    parser = argparse.ArgumentParser(formatter_class=lambda prog: argparse.RawTextHelpFormatter(prog, width=200), description="""example:
  python3 es.py -a PutIndex --index billing --data-file ../cost/tmp/imm-admin/2020-09-26.merge.json --keys "ProductCode,BillingDate,InstanceID"
  python3 es.py -a DelIndex --index billing
""")
    parser.add_argument("--host", default="127.0.0.1:9200", help="host")
    parser.add_argument("--username", help="username")
    parser.add_argument("--password", help="password")
    parser.add_argument("--data-file", help="data file")
    parser.add_argument("--index", help="index")
    parser.add_argument("--keys", help="keys")
    parser.add_argument("-a", "--action", help="action", choices=[
        "PutIndex", "DelIndex",
    ])
    args = parser.parse_args()
    if args.username:
        client = Elasticsearch(hosts=args.host.split(","), http_auth=(args.username, args.password), verify_certs=False)
    else:
        client = Elasticsearch(hosts=args.host.split(","))
    if args.action == "PutIndex":
        put_index(client, args.index, args.data_file, args.keys)
    elif args.action == "DelIndex":
        del_index(client, args.index)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()


