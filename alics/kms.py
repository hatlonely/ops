#!/usr/bin/env python3

import argparse
import json
import aksk

from aliyunsdkcore.client import AcsClient
from aliyunsdkkms.request.v20160120.ListKeysRequest import ListKeysRequest
from aliyunsdkkms.request.v20160120.EncryptRequest import EncryptRequest
from aliyunsdkkms.request.v20160120.DecryptRequest import DecryptRequest
from aliyunsdkkms.request.v20160120.GenerateDataKeyRequest import GenerateDataKeyRequest


def encrypt(client, key_id, text):
    req = EncryptRequest()
    req.set_accept_format('json')
    req.set_KeyId(key_id)
    req.set_Plaintext(text)
    res = client.do_action_with_exception(req)
    return json.loads(res)


def decrypt(client, text):
    req = DecryptRequest()
    req.set_CiphertextBlob(text)
    res = client.do_action_with_exception(req)
    return json.loads(res)


def list_keys(client):
    req = ListKeysRequest()
    res = client.do_action_with_exception(req)
    return json.loads(res)


def generate_data_key(client, key_id):
    req = GenerateDataKeyRequest()
    req.set_accept_format('json')
    req.set_KeyId(key_id)
    res = client.do_action_with_exception(req)
    return json.loads(res)


def main():
    parser = argparse.ArgumentParser(formatter_class=lambda prog: argparse.RawTextHelpFormatter(prog, width=200), description="""example:
  python3 kms.py -i ak -s sk -r cn-shanghai -a ListKeys
  python3 kms.py -i ak -s sk -r cn-shanghai -a Encrypt --content $(cat test.json | base64) -k xxx | jq -r .CiphertextBlob | tail -1 > test.blob
  python3 kms.py -i ak -s sk -r cn-shanghai -a Decrypt --content $(cat test.blob) | jq -r .Plaintext | tail -1 | base64 -d
""")
    parser.add_argument("-i", "--access-key-id", help="access key id")
    parser.add_argument("-s", "--access-key-secret", help="access key secret")
    parser.add_argument("-c", "--credential", help="credential file")
    parser.add_argument("-k", "--key-id", help="key id")
    parser.add_argument("-r", "--region-id", help="region id")
    parser.add_argument("-a", "--action", help="action", choices=["Encrypt", "Decrypt", "ListKeys", "GenerateDataKey"])
    parser.add_argument("--content", help="content")
    args = parser.parse_args()
    if args.credential:
        args.access_key_id, args.access_key_secret = aksk.load_from_file(args.credential)
    client = AcsClient(args.access_key_id, args.access_key_secret, args.region_id)
    if args.action == "Encrypt":
        print(json.dumps(encrypt(client, args.key_id, args.content)))
    elif args.action == "Decrypt":
        print(json.dumps(decrypt(client, args.content)))
    elif args.action == "ListKeys":
        print(json.dumps(list_keys(client)))
    elif args.action == "GenerateDataKey":
        print(json.dumps(generate_data_key(client, args.key_id)))
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
