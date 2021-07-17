#!/usr/bin/env python3

import argparse
import json
import aksk
import os
import oss2


def get_object(bucket: oss2.Bucket, obj, filename, override=False):
    if filename:
        filename = os.path.basename(obj)
    if not override:
        if os.path.exists(filename):
            return {"status": 304}
    res = bucket.get_object_to_file(obj, filename)
    return {"status": res.status}


def put_object(bucket: oss2.Bucket, obj, filename, override=False):
    if not override:
        if bucket.object_exists(obj):
            return {"status": 304}
    if obj:
        obj = os.path.basename(filename)
    res = bucket.put_object_from_file(obj, filename)
    return {"status": res.status}


def put_symlink(bucket: oss2.Bucket, obj, symlink):
    res = bucket.put_symlink(obj, symlink)
    return {"status": res.status}


def main():
    parser = argparse.ArgumentParser(formatter_class=lambda prog: argparse.RawTextHelpFormatter(prog, width=200), description="""example:
  python3 oss.py -i ak -s sk -r cn-shanghai -a PutSymlink --bucket imm-test-hl-shanghai --object 1.docx --symlink 1.link.pdf
  python3 oss.py -i ak -s sk -r cn-shanghai -a GetObject --bucket imm-test-hl-shanghai --object 1.docx --filename 1.docx
  python3 oss.py -i ak -s sk -r cn-shanghai -a PutObject --bucket imm-test-hl-shanghai --object 1.docx --filename 1.docx
""")
    parser.add_argument("-i", "--access-key-id", help="access key id")
    parser.add_argument("-s", "--access-key-secret", help="access key secret")
    parser.add_argument("-c", "--credential", help="credential file")
    parser.add_argument("-r", "--region-id", help="region id")
    parser.add_argument("-a", "--action", help="action", choices=[
        "PutSymlink", "PutObject", "GetObject"
    ])
    parser.add_argument("--bucket", help="bucket")
    parser.add_argument("--object", help="object")
    parser.add_argument("--symlink", help="symlink")
    parser.add_argument("--filename", help="filename")
    parser.add_argument("--override", type=bool, help="override")
    args = parser.parse_args()

    if args.credential:
        args.access_key_id, args.access_key_secret = aksk.load_from_file(args.credential)

    auth = oss2.Auth(args.access_key_id, args.access_key_secret)
    bucket = oss2.Bucket(auth, "http://oss-{}.aliyuncs.com".format(args.region_id), args.bucket)
    print(args.filename, args.object)
    if args.action == "PutSymlink":
        print(json.dumps(put_symlink(bucket, args.object, args.symlink)))
    elif args.action == "PutObject":
        print(json.dumps(put_object(bucket, args.object, args.filename, args.override)))
    elif args.action == "GetObject":
        print(json.dumps(get_object(bucket, args.object, args.filename, args.override)))
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
