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


def preview(endpoint, params, access_key_id, access_key_secret, security_token):
    # https://help.aliyun.com/document_detail/74947.html?spm=a2c4g.11186623.2.22.335226c5dUnarR
    params["accessKeyId"] = access_key_id
    params["accessKeySecret"] = access_key_secret
    if security_token:
        params["stsToken"] = urllib.parse.quote(security_token)
    res = requests.get(endpoint, params=params)
    return json.loads(json.dumps(urllib.parse.unquote(res.url)))


def do(endpoint, params, access_key_id, access_key_secret, security_token):
    if security_token:
        params["SecurityToken"] = security_token
    params = make_pop_params("POST", params, access_key_id, access_key_secret)
    res = requests.post(endpoint, params=params)
    return json.loads(res.text)


def main():
    parser = argparse.ArgumentParser(formatter_class=lambda prog: argparse.RawTextHelpFormatter(prog, width=200), description="""example:
  python3 imm.py -c ~/.aksk/imm-test -i ak -s sk -r cn-shanghai --request '{
    "Action": "GetOfficePreviewURL",
    "Project": "hl-shanghai-doc-project",
    "SrcUri": "oss://imm-test-hl-shanghai/1.docx"
  }'
  python3 imm.py -c ~/.aksk/imm-test -i ak -s sk -r cn-shanghai --request '{
    "Action": "GetOfficeEditURL",
    "Project": "hl-shanghai-doc-project",
    "SrcUri": "oss://imm-test-hl-shanghai/2.docx",
    "SrcType": "",
    "TgtUri": "oss://imm-test-hl-shanghai/2.docx/edit",
    "UserName": "test",
    "UserID": "1234",
    "NotifyTopicName": "imm-test-hl-mns-topic-shanghai",
    "NotifyEndpoint": "http://1023210024677934.mns.cn-shanghai-internal.aliyuncs.com/",
    "FileID": "1234"
  }'
""")
    parser.add_argument("-c", "--credential", help="credential file")
    parser.add_argument("-i", "--access-key-id", help="access key id")
    parser.add_argument("-s", "--access-key-secret", help="access key secret")
    parser.add_argument("-e", "--endpoint", help="endpoint")
    parser.add_argument("-r", "--region-id", help="region")
    parser.add_argument("--role", help="role")
    parser.add_argument("--owner-id", help="user id")
    parser.add_argument("--request", help="request")
    args = parser.parse_args()

    if args.credential:
        args.access_key_id, args.access_key_secret = aksk.load_from_file(args.credential)
    if not args.endpoint and args.region_id:
        args.endpoint = "https://imm.{}.aliyuncs.com".format(args.region_id)

    security_token = ''
    if args.owner_id and args.role:
        res = assume_role("https://sts.aliyuncs.com", args.access_key_id, args.access_key_secret, args.owner_id, args.role)
        args.access_key_id = res["Credentials"]["AccessKeyId"]
        args.access_key_secret = res["Credentials"]["AccessKeySecret"]
        security_token = res["Credentials"]["SecurityToken"]

    request = json.loads(args.request)
    if request["Action"] == "PreviewV1":
        del(request["Action"])
        preview("https://preview.imm.aliyuncs.com/index.html", request, args.access_key_id, args.access_key_secret, security_token)
    else:
        print(json.dumps(do(args.endpoint, request, args.access_key_id, args.access_key_secret, security_token)))


if __name__ == "__main__":
    main()
