#!/usr/bin/env python3

import argparse
import json
import aksk

from alibabacloud_rds20140815.client import Client as Rds20140815Client
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_rds20140815 import models as rds_20140815_models


def describe_db_instances(config: open_api_models.Config, region_id):
    req = rds_20140815_models.DescribeDBInstancesRequest()
    req.region_id = region_id
    instances = []
    while True:
        res = Rds20140815Client(config).describe_dbinstances(req)
        res = res.to_map()
        for instance in res["body"]["Items"]["DBInstance"]:
            instances.append(instance)
        if len(instances) >= res["body"]["TotalRecordCount"]:
            break
        req.page_number = res["body"]["PageNumber"] + 1
    return instances


def describe_db_instance_attribute(config: open_api_models.Config, region_id, instance_id, instance_name):
    if not instance_id:
        instances = describe_db_instances(config, region_id)
        for instance in instances:
            if instance["DBInstanceDescription"] == instance_name:
                instance_id = instance["DBInstanceId"]
                break
    req = rds_20140815_models.DescribeDBInstanceAttributeRequest()
    req.dbinstance_id = instance_id
    res = Rds20140815Client(config).describe_dbinstance_attribute(req)
    return res.to_map()["body"]["Items"]["DBInstanceAttribute"][0]


def main():
    parser = argparse.ArgumentParser(formatter_class=lambda prog: argparse.RawTextHelpFormatter(prog, width=200), description="""example:
  python3 rds.py -i ak -s sk -r cn-shanghai -a DescribeDBInstances
  python3 rds.py -i ak -s sk -r cn-shanghai -a DescribeDBInstanceAttribute --instance-id rm-uf6x9546140uj8rnv
  python3 rds.py -i ak -s sk -r cn-shanghai -a DescribeDBInstanceAttribute --instance-name weboffice-regression-rds
""")
    parser.add_argument("-i", "--access-key-id", help="access key id")
    parser.add_argument("-s", "--access-key-secret", help="access key secret")
    parser.add_argument("-r", "--region-id", help="region id")
    parser.add_argument("-a", "--action", help="action", choices=["DescribeDBInstances", "DescribeDBInstanceAttribute"])
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
    if args.action == "DescribeDBInstances":
        print(json.dumps(describe_db_instances(config, args.region_id)))
    elif args.action == "DescribeDBInstanceAttribute":
        print(json.dumps(describe_db_instance_attribute(config, args.region_id, args.instance_id, args.instance_name)))
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
