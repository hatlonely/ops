#!/usr/bin/env python3

import re
import json
import argparse
import aksk
import vpc

from alibabacloud_ecs20140526.client import Client as Ecs20140526Client
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_ecs20140526 import models as ecs_20140526_models


def describe_regions(config: open_api_models.Config):
    req = ecs_20140526_models.DescribeInstancesRequest()
    res = Ecs20140526Client(config).describe_regions(req)
    return res.to_map()["body"]["Regions"]["Region"]


def describe_instances(config: open_api_models.Config, region_id, instance_id, instance_name, vpc_id, vpc_name, public_ip, private_ip):
    req = ecs_20140526_models.DescribeInstancesRequest()
    req.region_id = region_id
    if instance_name:
        req.instance_name = "*" + instance_name + "*"
    if instance_id:
        req.instance_ids = json.dumps(instance_id.split(","))
    if vpc_id:
        req.vpc_id = vpc_id
    if not vpc_id and vpc_name:
        res = vpc.describe_vpcs(config, region_id, vpc_id, vpc_name)
        req.vpc_id = res[0]["VpcId"]
    if public_ip:
        req.public_ip_addresses = json.dumps([public_ip])
    if private_ip:
        req.private_ip_addresses = json.dumps([private_ip])

    instances = []
    count = 0
    while True:
        res = Ecs20140526Client(config).describe_instances(req)
        res = res.to_map()["body"]
        for instance in res["Instances"]["Instance"]:
            instances.append(instance)
        if len(instances) >= res["TotalCount"] or count >= 100:
            break
        count += 1
        req.page_number = res["PageNumber"] + 1
    return instances


def describe_price(config: open_api_models.Config, region_id, instance_type):
    req = ecs_20140526_models.DescribePriceRequest()
    req.instance_type = instance_type
    req.region_id = region_id
    res = Ecs20140526Client(config).describe_price(req)
    return res.to_map()["body"]["PriceInfo"]


def describe_security_groups(config: open_api_models.Config, region_id, security_group_name, vpc_id, vpc_name):
    req = ecs_20140526_models.DescribeSecurityGroupsRequest()
    req.region_id = region_id
    req.vpc_id = vpc_id
    if not vpc_id and vpc_name:
        res = vpc.describe_vpcs(config, region_id, vpc_id, vpc_name)
        req.vpc_id = res[0]["VpcId"]

    security_groups = []
    count = 0
    while True:
        res = Ecs20140526Client(config).describe_security_groups(req)
        res = res.to_map()["body"]
        for security_group in res["SecurityGroups"]["SecurityGroup"]:
            security_groups.append(security_group)
        if len(security_groups) >= res["TotalCount"] or count >= 100:
            break
        count += 1
        req.page_number = res["PageNumber"] + 1
    if not security_group_name:
        return security_groups
    pattern = re.compile(".*" + security_group_name + ".*")
    return [x for x in security_groups if pattern.match(x["SecurityGroupName"])]


def modify_security_group_rule(config: open_api_models.Config, region_id, security_group_id, security_group_name, vpc_id, vpc_name, cidr_ip, ip_protocol="all", port_range="-1/-1"):
    req = ecs_20140526_models.ModifySecurityGroupRuleRequest()
    req.region_id = region_id
    req.ip_protocol = ip_protocol
    req.port_range = port_range
    req.source_cidr_ip = cidr_ip
    if security_group_id:
        req.security_group_id = security_group_id
    if security_group_name:
        res = describe_security_groups(config, region_id, security_group_name, vpc_id, vpc_name)
        req.security_group_id = res[0]["SecurityGroupId"]
    res = Ecs20140526Client(config).modify_security_group_rule(req)
    return res.to_map()["body"]


def authorize_security_group(config: open_api_models.Config, region_id, security_group_id, security_group_name, vpc_id, vpc_name, cidr_ip, ip_protocol="all", port_range="-1/-1"):
    req = ecs_20140526_models.AuthorizeSecurityGroupRequest()
    req.region_id = region_id
    req.ip_protocol = ip_protocol
    req.port_range = port_range
    req.source_cidr_ip = cidr_ip
    if security_group_id:
        req.security_group_id = security_group_id
    if security_group_name:
        res = describe_security_groups(config, region_id, security_group_name, vpc_id, vpc_name)
        req.security_group_id = res[0]["SecurityGroupId"]
    req.description = "create by ecs.py"
    res = Ecs20140526Client(config).authorize_security_group(req)
    return res.to_map()["body"]


def create_security_group(config: open_api_models.Config, region_id, security_group_name, vpc_id, vpc_name):
    req = ecs_20140526_models.CreateSecurityGroupRequest()
    req.region_id = region_id
    if vpc_id:
        req.vpc_id = vpc_id
    if not vpc_id and vpc_name:
        res = vpc.describe_vpcs(config, region_id, vpc_id, vpc_name)
        req.vpc_id = res[0]["VpcId"]
    req.security_group_name = security_group_name
    req.description = "create by ecs.py"
    res = Ecs20140526Client(config).create_security_group(req)
    return res.to_map()["body"]


def join_security_group(config: open_api_models.Config, region_id, instance_id, security_group_id):
    req = ecs_20140526_models.JoinSecurityGroupRequest()
    req.region_id = region_id
    req.instance_id = instance_id
    req.security_group_id = security_group_id
    res = Ecs20140526Client(config).join_security_group(req)
    return res.to_map()["body"]


def add_access_control_to_security_group(config: open_api_models.Config, region_id, security_group_name, instance_id, instance_name, vpc_id, vpc_name, cidr_ip, ip_protocol, port_range):
    instance = None
    if instance_id or instance_name:
        res = describe_instances(config, region_id, instance_id, instance_name, None, vpc_name, None, None)
        vpc_id = res[0]["VpcAttributes"]["VpcId"]
        instance = res[0]
    res = describe_security_groups(config, region_id, security_group_name, vpc_id, vpc_name)
    if not res:
        res = create_security_group(config, region_id, security_group_name, vpc_id, vpc_name)
        security_group_id = res["SecurityGroupId"]
    else:
        security_group_id = res[0]["SecurityGroupId"]
    res = authorize_security_group(config, region_id, None, security_group_name, vpc_id, vpc_name, cidr_ip, ip_protocol, port_range)
    if instance:
        if security_group_id not in instance["SecurityGroupIds"]["SecurityGroupId"]:
            join_security_group(config, region_id, instance["InstanceId"], security_group_id)
    return res


def main():
    parser = argparse.ArgumentParser(formatter_class=lambda prog: argparse.RawTextHelpFormatter(prog, width=200), description="""example:
  python3 ecs.py -c ~/.aksk/imm-dev -r cn-shanghai -a DescribeRegions
  python3 ecs.py -c ~/.aksk/imm-dev -r cn-shanghai -a DescribePrice --instance-type ecs.sn1ne.2xlarge
  python3 ecs.py -c ~/.aksk/imm-dev -r cn-shanghai -a DescribeInstances --instance-name hl | jq ".[].InstanceType" | sort | uniq -c
  python3 ecs.py -c ~/.aksk/imm-dev -r cn-shanghai -a DescribeInstances --public-ip 47.116.74.14 | jq ".[].InstanceType" | sort | uniq -c
  python3 ecs.py -c ~/.aksk/imm-dev -r cn-shanghai -a DescribeInstances --instance-name hl | jq -r '.[] | "\(.InstanceType) \(.CpuOptions.CoreCount) \(.CpuOptions.ThreadsPerCore) \(.Memory)M"'
  python3 ecs.py -c ~/.aksk/imm-dev -r cn-shanghai -a DescribeSecurityGroups --vpc-name imm-dev-hl-vpc-shanghai-ecs --security-group-name imm-dev-hl-security-group
  python3 ecs.py -c ~/.aksk/imm-dev -r cn-shanghai -a AddAccessControlToSecurityGroup --vpc-name imm-dev-hl-vpc-shanghai-ecs --security-group-name imm-dev-hl-security-group --ip "$(wget -qO - icanhazip.com)"
  python3 ecs.py -c ~/.aksk/imm-dev -r cn-shanghai -a AddAccessControlToSecurityGroup --instance-name imm-dev-hl-ecs --security-group-name imm-dev-hl-security-group --ip "$(wget -qO - icanhazip.com)"
""")
    parser.add_argument("-i", "--access-key-id", help="access key id")
    parser.add_argument("-s", "--access-key-secret", help="access key secret")
    parser.add_argument("-c", "--credential", help="credential file")
    parser.add_argument("-r", "--region-id", help="region id")
    parser.add_argument("-a", "--action", help="action", choices=[
        "DescribeRegions", "DescribeInstances", "DescribePrice", "DescribeSecurityGroups",
        "AddAccessControlToSecurityGroup"
    ])
    parser.add_argument("--instance-name", help="instance name")
    parser.add_argument("--instance-type", help="instance type")
    parser.add_argument("--instance-id", help="instance id")
    parser.add_argument("--vpc-id", help="vpc id")
    parser.add_argument("--vpc-name", help="vpc name")
    parser.add_argument("--security-group-name", help="security group name")
    parser.add_argument("--ip", help="ip")
    parser.add_argument("--port-range", default="-1/-1", help="ip")
    parser.add_argument("--ip-protocol", default="all", help="ip protocol")
    parser.add_argument("--public-ip", help="public ip")
    parser.add_argument("--private-ip", help="private ip")
    args = parser.parse_args()
    if args.credential:
        args.access_key_id, args.access_key_secret = aksk.load_from_file(args.credential)
    config = open_api_models.Config(
        access_key_id=args.access_key_id,
        access_key_secret=args.access_key_secret,
        region_id=args.region_id,
    )

    if args.action == "DescribeRegions":
        print(json.dumps(describe_regions(config)))
    elif args.action == "DescribeInstances":
        print(json.dumps(describe_instances(config, args.region_id, args.instance_id, args.instance_name, args.vpc_id, args.vpc_name, args.public_ip, args.private_ip)))
    elif args.action == "DescribePrice":
        print(json.dumps(describe_price(config, args.region_id, args.instance_type)))
    elif args.action == "DescribeSecurityGroups":
        print(json.dumps(describe_security_groups(config, args.region_id, args.security_group_name, args.vpc_id, args.vpc_name)))
    elif args.action == "AddAccessControlToSecurityGroup":
        print(json.dumps(add_access_control_to_security_group(
            config, args.region_id, args.security_group_name, args.instance_id, args.instance_name, args.vpc_id, args.vpc_name, args.ip, args.ip_protocol, args.port_range
        )))
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
