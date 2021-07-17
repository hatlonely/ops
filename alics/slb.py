#!/usr/bin/env python3

import argparse
import json
import aksk

from alibabacloud_slb20140515.client import Client as Slb20140515Client
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_slb20140515 import models as slb_20140515_models


def describe_load_balancers(config: open_api_models.Config, region_id, load_balancer_id, load_balancer_name):
    req = slb_20140515_models.DescribeLoadBalancersRequest()
    req.region_id = region_id
    req.page_size = 10
    if load_balancer_name:
        req.load_balancer_name = load_balancer_name
    if load_balancer_id:
        req.load_balancer_id = load_balancer_id
    balancers = []
    while True:
        res = Slb20140515Client(config).describe_load_balancers(req)
        res = res.to_map()["body"]
        for balancer in res["LoadBalancers"]["LoadBalancer"]:
            balancers.append(balancer)
        if len(balancers) >= res["TotalCount"]:
            break
        req.page_number = res["PageNumber"] + 1
    return balancers


def describe_load_balancer_attribute(config: open_api_models.Config, region_id, load_balancer_id, load_balancer_name):
    if not load_balancer_id:
        balancers = describe_load_balancers(config, region_id, None, load_balancer_name)
        for balancer in balancers:
            if balancer["LoadBalancerName"] == load_balancer_name:
                load_balancer_id = balancer["LoadBalancerId"]
                break
    req = slb_20140515_models.DescribeLoadBalancerAttributeRequest()
    req.region_id= region_id
    req.load_balancer_id = load_balancer_id
    res = Slb20140515Client(config).describe_load_balancer_attribute(req)
    return res.to_map()["body"]


def describe_access_control_lists(config: open_api_models.Config, region_id):
    req = slb_20140515_models.DescribeAccessControlListsRequest()
    req.region_id = region_id
    req.page_size = 10
    acls = []
    while True:
        res = Slb20140515Client(config).describe_access_control_lists(req)
        res = res.to_map()["body"]
        for acl in res["Acls"]["Acl"]:
            acls.append(acl)
        if len(acls) >= res["TotalCount"]:
            break
        req.page_number = res["PageNumber"] + 1
    return acls


def describe_access_control_list_attribute(config: open_api_models.Config, region_id, acl_id, acl_name):
    if not acl_id:
        acls = describe_access_control_lists(config, region_id)
        for acl in acls:
            if acl["AclName"] == acl_name:
                acl_id = acl["AclId"]
    req = slb_20140515_models.DescribeAccessControlListAttributeRequest()
    req.region_id = region_id
    req.acl_id = acl_id
    res = Slb20140515Client(config).describe_access_control_list_attribute(req)
    return res.to_map()["body"]


def add_access_control_list_entry(config: open_api_models.Config, region_id, acl_id, acl_name, ip):
    if not acl_id:
        acls = describe_access_control_lists(config, region_id)
        for acl in acls:
            if acl["AclName"] == acl_name:
                acl_id = acl["AclId"]
    req = slb_20140515_models.AddAccessControlListEntryRequest()
    req.region_id = region_id
    req.acl_id = acl_id
    req.acl_entrys = json.dumps([{"entry": "{}/32".format(ip), "comment": "auto add by slb.py"}])
    res = Slb20140515Client(config).add_access_control_list_entry(req)
    return res.to_map()["body"]


def create_load_balancer_tcplistener(config: open_api_models.Config, acl_id, listener_port, backend_port):
    req = slb_20140515_models.CreateLoadBalancerTCPListenerRequest()
    req.acl_id = acl_id
    req.listener_port = listener_port
    req.backend_server_port = backend_port
    res = Slb20140515Client(config).create_load_balancer_tcplistener(req)
    return res.to_map()["body"]


def main():
    parser = argparse.ArgumentParser(formatter_class=lambda prog: argparse.RawTextHelpFormatter(prog, width=200), description="""example:
  python3 slb.py -i ak -s sk -r cn-shanghai -a DescribeLoadBalancers
  python3 slb.py -i ak -s sk -r cn-shanghai -a DescribeAccessControlLists
  python3 slb.py -i ak -s sk -r cn-shanghai -a DescribeAccessControlListAttribute --acl-name weboffice
  python3 slb.py -i ak -s sk -r cn-shanghai -a DescribeAccessControlListAttribute --acl-id acl-uf6oj1uhti7tf2wd3qdtg
  python3 slb.py -i ak -s sk -r cn-shanghai -a AddAccessControlListEntry --acl-name weboffice --ip "$(wget -qO - icanhazip.com)"
  python3 slb.py -i ak -s sk -r cn-shanghai -a AddAccessControlListEntry --acl-name weboffice --ip "$(dig +short myip.opendns.com @resolver1.opendns.com)"
""")
    parser.add_argument("-i", "--access-key-id", help="access key id")
    parser.add_argument("-s", "--access-key-secret", help="access key secret")
    parser.add_argument("-c", "--credential", help="credential file")
    parser.add_argument("-r", "--region-id", help="region id")
    parser.add_argument("--load-balancer-name", help="load balancer name")
    parser.add_argument("--load-balancer-id", help="load balancer id")
    parser.add_argument("--ip", help="ip")
    parser.add_argument("--acl-id", help="acl id")
    parser.add_argument("--acl-name", help="acl name")
    parser.add_argument("--listener-port", help="listener port")
    parser.add_argument("--backend-port", help="backend port")
    parser.add_argument("-a", "--action", help="action", choices=[
        "DescribeLoadBalancerAttribute", "DescribeLoadBalancers", "DescribeAccessControlLists", "DescribeAccessControlListAttribute",
        "AddAccessControlListEntry", "CreateLoadBalancerTCPListener"
    ])
    args = parser.parse_args()
    if args.credential:
        args.access_key_id, args.access_key_secret = aksk.load_from_file(args.credential)
    config = open_api_models.Config(
        access_key_id=args.access_key_id,
        access_key_secret=args.access_key_secret,
        region_id=args.region_id,
    )

    if args.action == "DescribeLoadBalancers":
        print(json.dumps(describe_load_balancers(config, args.region_id, args.load_balancer_id, args.load_balancer_name)))
    elif args.action == "DescribeLoadBalancerAttribute":
        print(json.dumps(describe_load_balancer_attribute(config, args.region_id, args.load_balancer_id, args.load_balancer_name)))
    elif args.action == "DescribeAccessControlLists":
        print(json.dumps(describe_access_control_lists(config, args.region_id)))
    elif args.action == "DescribeAccessControlListAttribute":
        print(json.dumps(describe_access_control_list_attribute(config, args.region_id, args.acl_id, args.acl_name)))
    elif args.action == "AddAccessControlListEntry":
        print(json.dumps(add_access_control_list_entry(config, args.region_id, args.acl_id, args.acl_name, args.ip)))
    elif args.action == "CreateLoadBalancerTCPListener":
        print(json.dumps(create_load_balancer_tcplistener(config, args.acl_id, args.listener_port, args.backend_port)))
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
