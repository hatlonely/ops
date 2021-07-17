#!/usr/bin/env python3

import argparse
import json
import aksk


from alibabacloud_vpc20160428.client import Client as Vpc20160428Client
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_vpc20160428 import models as vpc_20160428_models


def create_vpc(config: open_api_models.Config, region_id, vpc_name, cidr_block, description):
    res = describe_vpcs(config, region_id, None, vpc_name)
    if len(res) != 0:
        return res[0]
    req = vpc_20160428_models.CreateVpcRequest()
    req.region_id = region_id
    req.cidr_block = cidr_block
    req.vpc_name = vpc_name
    req.description = description
    res = Vpc20160428Client(config).create_vpc(req)
    return res.to_map()["body"]


def describe_vpcs(config: open_api_models.Config, region_id, vpc_id, vpc_name):
    req = vpc_20160428_models.DescribeVpcsRequest()
    req.region_id = region_id
    if vpc_id:
        req.vpc_id = vpc_id
    if vpc_name:
        req.vpc_name = vpc_name
    vpcs = []
    while True:
        res = Vpc20160428Client(config).describe_vpcs(req)
        res = res.to_map()["body"]
        for vpc in res["Vpcs"]["Vpc"]:
            vpcs.append(vpc)
        if len(vpcs) >= res["TotalCount"]:
            break
        req.page_number = res["PageNumber"] + 1
    return vpcs


def describe_vswitches(config: open_api_models.Config, region_id, vpc_id, vpc_name, vswitch_name):
    req = vpc_20160428_models.DescribeVSwitchesRequest()
    req.region_id = region_id
    if vpc_id:
        req.vpc_id = vpc_id
    if not vpc_id and vpc_name:
        res = describe_vpcs(config, region_id, None, vpc_name)
        req.vpc_id = res[0]["VpcId"]
    res = Vpc20160428Client(config).describe_vswitches(req)
    res = res.to_map()["body"]["VSwitches"]["VSwitch"]
    if vswitch_name:
        return [x for x in res if x["VSwitchName"].startswith(vswitch_name)]
    return res


def main():
    parser = argparse.ArgumentParser(formatter_class=lambda prog: argparse.RawTextHelpFormatter(prog, width=200), description="""example:
  python3 vpc.py -i ak -s sk -r cn-shanghai -a CreateVpc --cidr-block "10.0.0.0/8" --vpc-name imm-dev-hl-vpc-bc
  python3 vpc.py -i ak -s sk -r cn-shanghai -a DescribeVpcs --vpc-name imm-dev-hl-vpc-shanghai-ecs
""")
    parser.add_argument("-i", "--access-key-id", help="access key id")
    parser.add_argument("-s", "--access-key-secret", help="access key secret")
    parser.add_argument("-c", "--credential", help="credential file")
    parser.add_argument("-r", "--region-id", help="region id")
    parser.add_argument("--vpc-id", help="vpc id")
    parser.add_argument("--vpc-name", help="vpc name")
    parser.add_argument("--cidr-block", help="cidr block")
    parser.add_argument("--vswitch-name", help="vswitch name")
    parser.add_argument("--description", default="create by vpc.py", help="description")
    parser.add_argument("-a", "--action", help="action", choices=[
        "CreateVpc", "DescribeVpcs", "DescribeVSwitches"
    ])
    args = parser.parse_args()
    if args.credential:
        args.access_key_id, args.access_key_secret = aksk.load_from_file(args.credential)
    config = open_api_models.Config(
        access_key_id=args.access_key_id,
        access_key_secret=args.access_key_secret,
        region_id=args.region_id,
    )
    if args.action == "CreateVpc":
        print(json.dumps(create_vpc(config, args.region_id, args.vpc_name, args.cidr_block, args.description)))
    elif args.action == "DescribeVpcs":
        print(json.dumps(describe_vpcs(config, args.region_id, args.vpc_id, args.vpc_name)))
    elif args.action == "DescribeVSwitches":
        print(json.dumps(describe_vswitches(config, args.region_id, args.vpc_id, args.vpc_name, args.vswitch_name)))
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
