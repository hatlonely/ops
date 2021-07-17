#!/usr/bin/env python3

import argparse
import json
import aksk

from alibabacloud_r_kvstore20150101.client import Client as R_kvstore20150101Client
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_r_kvstore20150101 import models as r_kvstore_20150101_models


def describe_instances(config: open_api_models.Config, region_id):
    req = r_kvstore_20150101_models.DescribeInstancesRequest()
    req.region_id = region_id
    instances = []
    while True:
        res = R_kvstore20150101Client(config).describe_instances(req)
        res = res.to_map()["body"]
        for instance in res["Instances"]["KVStoreInstance"]:
            instances.append(instance)
        if len(instances) >= res["TotalCount"]:
            break
        req.page_number = res["PageNumber"] + 1
    return instances


def describe_instance_attribute(config: open_api_models.Config, region_id, instance_id, instance_name):
    req = r_kvstore_20150101_models.DescribeInstanceAttributeRequest()
    if not instance_id:
        instances = describe_instances(config, region_id)
        for instance in instances:
            if instance["InstanceName"] == instance_name:
                instance_id = instance["InstanceId"]
                break
    req.instance_id = instance_id
    res = R_kvstore20150101Client(config).describe_instance_attribute(req)
    return res.to_map()["body"]["Instances"]["DBInstanceAttribute"][0]


def main():
    parser = argparse.ArgumentParser(formatter_class=lambda prog: argparse.RawTextHelpFormatter(prog, width=200), description="""example:
  python3 redis.py -i ak -s sk -r cn-shanghai -a DescribeInstances
  python3 redis.py -i ak -s sk -r cn-shanghai -a DescribeInstanceAttribute --instance-name weboffice-regression-redis
""")
    parser.add_argument("-i", "--access-key-id", help="access key id")
    parser.add_argument("-s", "--access-key-secret", help="access key secret")
    parser.add_argument("-r", "--region-id", help="region id")
    parser.add_argument("-a", "--action", help="action", choices=["DescribeInstances", "DescribeInstanceAttribute"])
    parser.add_argument("-c", "--credential", help="credential file")
    parser.add_argument("--instance-id", help="instance id")
    parser.add_argument("--instance-name", help="instance name")
    args = parser.parse_args()
    if args.credential:
        args.access_key_id, args.access_key_secret = aksk.load_from_file(args.credential)
    config = open_api_models.Config(
        access_key_id=args.access_key_id,
        access_key_secret=args.access_key_secret,
        region_id=args.region_id,
    )

    if args.action == "DescribeInstances":
        print(json.dumps(describe_instances(config, args.region_id)))
    elif args.action == "DescribeInstanceAttribute":
        print(json.dumps(describe_instance_attribute(config, args.region_id, args.instance_id, args.instance_name)))
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
