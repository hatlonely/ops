#!/usr/bin/env python3

import argparse
import json
import re

from alibabacloud_tea_openapi import models as open_api_models


product_info = {
    "slb": "alibabacloud_slb20140515",
    "ack": "alibabacloud_cs20151215",
    "rds": "alibabacloud_rds20140815",
    "redis": "alibabacloud_r_kvstore20150101",
    "ecs": "alibabacloud_ecs20140526",
    "vpc": "alibabacloud_vpc20160428",
    "ram": "alibabacloud_ram20150501",
    "sts": "alibabacloud_sts20150401",
}


def snake_case(name):
    return re.sub("([A-Z]+[a-z0-9]+)", r"\1_", name).lower()[:-1]


def do(config, region_id, product_id, action, request):
    if "RegionId" not in request:
        request["RegionId"] = region_id
    if "Action" not in request:
        request["Action"] = action
    if not action:
        action = request["Action"]

    module_name = product_info[product_id]
    module_client = __import__("{}.client".format(module_name), fromlist=["Client"])
    module = __import__(product_info[product_id], fromlist=["models"])

    client = getattr(module_client, "Client")(config)

    req = getattr(getattr(module, "models"), "{}Request".format(action))().from_map(request)
    res = getattr(client, snake_case(action))(req)
    return res.to_map()["body"]


def main():
    parser = argparse.ArgumentParser(formatter_class=lambda prog: argparse.RawTextHelpFormatter(prog, width=200), description="""example:
  python3 acsv2.py -i ak -s sk -r cn-shanghai -p slb -a DescribeLoadBalancers --request '{}'
  python3 acsv2.py -i ak -s sk -e ram.aliyuncs.com -p ram -a GetUser --request '{
    "UserName": "imm-test-hl"
  }'
""")
    parser.add_argument("-i", "--access-key-id", help="access key id")
    parser.add_argument("-s", "--access-key-secret", help="access key secret")
    parser.add_argument("-r", "--region-id", help="region id")
    parser.add_argument("-a", "--action", help="action")
    parser.add_argument("-p", "--product-id", help="product id")
    parser.add_argument("-e", "--endpoint", help="endpoint")
    parser.add_argument("--request", help="request")
    args = parser.parse_args()
    config = open_api_models.Config(
        access_key_id=args.access_key_id,
        access_key_secret=args.access_key_secret,
        region_id=args.region_id,
        endpoint=args.endpoint,
    )
    print(json.dumps(do(config, args.region_id, args.product_id, args.action, json.loads(args.request))))


if __name__ == "__main__":
    main()
