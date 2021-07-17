#!/usr/bin/env python3

import argparse
import base64
import datetime
import hmac
import json
import random
import urllib
import requests
import aksk


def encode(message):
    return urllib.parse.quote(str(message), safe='', encoding="utf-8").replace("+", "%20").replace("*", "%2A").replace("%7E", "~")


def signature(methods, params, access_key_secret):
    kvs = "&".join([
        "{}={}".format(encode(i), encode(params[i])) for i in sorted(params)
    ])
    to_sign = methods + "&" + encode("/") + "&" + "" + encode(kvs)
    return base64.b64encode(hmac.new((access_key_secret + '&').encode(), to_sign.encode(), digestmod='sha1').digest()).decode()


def make_pop_params(methods, params, access_key_id, access_key_secret):
    params["AccessKeyId"] = access_key_id
    if "Format" not in params:
        params["Format"] = "JSON"
    if "Version" not in params:
        params["Version"] = "2017-09-06"
    if "Timestamp" not in params:
        params["Timestamp"] = datetime.datetime.utcnow().isoformat()
    if "SignatureMethod" not in params:
        params["SignatureMethod"] = "HMAC-SHA1"
    if "SignatureVersion" not in params:
        params["SignatureVersion"] = "1.0"
    if "SignatureNonce" not in params:
        params["SignatureNonce"] = random.randint(0, 2**63-1)
    params["Signature"] = signature(methods, params, access_key_secret)
    return params


def assume_role(endpoint, access_key_id, access_key_secret, owner_id, role):
    # https://help.aliyun.com/document_detail/28763.html?spm=a2c4g.11186623.6.805.78927ffb2YnPpi
    params = {
        "Action": "AssumeRole",
        "Version": "2015-04-01",
        "RoleArn": "acs:ram::{}:role/{}".format(owner_id, role),
        "RoleSessionName": "test",
        "DurationSeconds": 3600,
    }
    params = make_pop_params("POST", params, access_key_id, access_key_secret)

    res = requests.post(endpoint, params=params)
    return json.loads(res.text)


def do(endpoint, params, access_key_id, access_key_secret, security_token):
    if security_token:
        params["SecurityToken"] = security_token
    params = make_pop_params("POST", params, access_key_id, access_key_secret)
    res = requests.post(endpoint, params=params)
    return json.loads(res.text)


def main():
    parser = argparse.ArgumentParser(formatter_class=lambda prog: argparse.RawTextHelpFormatter(prog, width=200), description="""example:
  python3 pop.py -c ~/.aksk/ccp-admin -i ak -s sk -e https://slb-share.cn-zhangjiakou.aliyuncs.com --request '{
    "Action": "InnerQueryLoadbalancerByInstanceId",
    "RegionId": "cn-zhangjiakou",
    "LoadBalancerId": "lb-8vb3wrwhxvr00i27rxjh4",
    "Version": "2014-05-15"
  }' | jq -r .Data | jq .
  python3 pop.py -c ~/.aksk/imm-test -i ak -s sk -e https://imm.cn-shanghai.aliyuncs.com --request '{
    "Action": "GetOfficeEditURL",
    "Project": "hl-shanghai-doc-project",
    "SrcUri": "oss://imm-test-hl-shanghai/1.docx",
    "SrcType": "",
    "TgtUri": "oss://imm-test-hl-shanghai/1.docx/edit",
    "UserName": "test",
    "UserID": "1234",
    "NotifyTopicName": "imm-test-hl-mns-topic-shanghai",
    "NotifyEndpoint": "http://1023210024677934.mns.cn-shanghai-internal.aliyuncs.com/",
    "FileID": "1234",
    "Version": "2017-09-06"
  }'
""")
    parser.add_argument("-c", "--credential", help="credential file")
    parser.add_argument("-i", "--access-key-id", help="access key id")
    parser.add_argument("-s", "--access-key-secret", help="access key secret")
    parser.add_argument("-e", "--endpoint", required=True, help="endpoint")
    parser.add_argument("--role", help="role")
    parser.add_argument("--owner-id", help="user id")
    parser.add_argument("--request", help="request")
    args = parser.parse_args()

    if args.credential:
        args.access_key_id, args.access_key_secret = aksk.load_from_file(args.credential)

    security_token = ''
    if args.owner_id and args.role:
        res = assume_role("https://sts.aliyuncs.com", args.access_key_id, args.access_key_secret, args.owner_id, args.role)
        args.access_key_id = res["Credentials"]["AccessKeyId"]
        args.access_key_secret = res["Credentials"]["AccessKeySecret"]
        security_token = res["Credentials"]["SecurityToken"]

    request = json.loads(args.request)
    print(json.dumps(do(args.endpoint, request, args.access_key_id, args.access_key_secret, security_token)))


if __name__ == "__main__":
    main()
