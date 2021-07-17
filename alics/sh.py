#!/usr/bin/env python3

import shlex
import json
import argparse
import base64
import diff


def analyst_shell_script(filename):
    tokens = list(shlex.shlex(open(filename).read(), punctuation_chars=True))
    kvs = {}
    for i in range(len(tokens)):
        if tokens[i] == "$" and tokens[i+1] == "cmd" and tokens[i+2] == "--endpoints" and tokens[i+3] == "$" and tokens[i+4] == "endpoint" and tokens[i+5] == "put":
            key = tokens[i+6]
            val = tokens[i+7]
            if val.startswith("'") and val.endswith("'"):
                val = val[1:-1]
            kvs[tokens[i+6]] = val
    return kvs


def diff_etcd_config(new_config, old_config):
    newc = json.loads(open(new_config).read())
    oldc_origin = json.loads(open(old_config).read())
    oldc={}
    for item in oldc_origin["kvs"]:
        key = base64.b64decode(item["key"]).decode()
        val = base64.b64decode(item["value"]).decode()
        if key in newc:
            oldc[key] = val
    if all([oldc.get(key) == newc.get(key) for key in newc]):
        return
    for key in oldc:
        if oldc[key] == newc[key]:
            continue
        print(key)
        diff.color_diff_text(oldc[key], newc[key])
    for key in newc:
        if key in oldc:
            continue
        print(key)
        diff.color_diff_text("", newc[key])


def main():
    parser = argparse.ArgumentParser(formatter_class=lambda prog: argparse.RawTextHelpFormatter(prog, width=200), description="""example:
  python3 sh.py -a AnalystShellScript -f "../weboffice/tmp/etcd-config.sh"
  python3 sh.py -a DiffEtcdConfig --new-file "../weboffice/tmp/etcd_new_config.json" --old-file "../weboffice/tmp/etcd_old_config.json"
""")
    parser.add_argument("-f", "--file", help="shell scripts file")
    parser.add_argument("--new-file", help="new etcd config")
    parser.add_argument("--old-file", help="old etcd config")
    parser.add_argument("-a", "--action", help="action")
    args = parser.parse_args()
    if args.action == "AnalystShellScript":
        print(json.dumps(analyst_shell_script(args.file)))
    elif args.action == "DiffEtcdConfig":
        diff_etcd_config(args.new_file, args.old_file)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()