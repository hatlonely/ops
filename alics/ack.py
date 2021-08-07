#!/usr/bin/env python3

import json
import argparse
import aksk
import acsv2

from alibabacloud_cs20151215.client import Client as CS20151215Client
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_cs20151215 import models as cs20151215_models


def describe_clusters(config: open_api_models.Config):
    req = cs20151215_models.DescribeClustersRequest()
    res = CS20151215Client(config).describe_clusters(req)
    return res.to_map()["body"]


def describe_cluster_detail(config: open_api_models.Config, cluster_id, cluster_name):
    if not cluster_id:
        res = describe_clusters(config)
        for cluster in res:
            if cluster["name"] == cluster_name:
                cluster_id = cluster["cluster_id"]
                break
    res = CS20151215Client(config).describe_cluster_detail(cluster_id)
    return res.to_map()["body"]


def describe_cluster_resources(config: open_api_models.Config, cluster_id, cluster_name):
    if not cluster_id:
        res = describe_clusters(config)
        for cluster in res:
            if cluster["name"] == cluster_name:
                cluster_id = cluster["cluster_id"]
                break
    res = CS20151215Client(config).describe_cluster_resources(cluster_id)
    return res.to_map()["body"]


def describe_cluster_user_kubeconfig(config: open_api_models.Config, cluster_id):
    req = cs20151215_models.DescribeClusterUserKubeconfigRequest()
    res = CS20151215Client(config).describe_cluster_user_kubeconfig(cluster_id, req)
    return res.to_map()["body"]


def add_master_to_slb(config: open_api_models.Config, region_id, cluster_id, cluster_name, slb_id, acl_id):
    cluster = describe_cluster_detail(config, cluster_id, cluster_name)
    cluster_id = cluster["cluster_id"]
    cluster_name = cluster["name"]
    resources = describe_cluster_resources(config, cluster_id, None)
    ecs_instance_ids = []
    for resource in resources:
        if resource["resource_type"] == "ALIYUN::ECS::InstanceGroup":
            ecs_instance_ids.append(resource["instance_id"])

    create_load_balancer_tcp_listener_res = acsv2.do(config, region_id, "slb", "CreateLoadBalancerTCPListener", {
        "ListenerPort": 6443,
        "BackendServerPort": 6443,
        "Bandwidth": -1,
        "LoadBalancerId": slb_id,
        "Scheduler": "wrr",
        "AclId": acl_id,
        "AclType": "white",
        "AclStatus": "on",
        "Description": cluster_name
    })
    add_backend_servers_res = acsv2.do(config, region_id,  "slb", "AddBackendServers", {
        "LoadBalancerId": slb_id,
        "BackendServers": json.dumps([{
            "ServerId": x,
            "Weight": "100",
            "Type": "ecs",
            "Port": "80",
            "Description": "k8s-master-{}".format(resources[0]["cluster_id"]),
        } for x in ecs_instance_ids])
    })
    set_load_balancer_status_res = acsv2.do(config, region_id, "slb", "SetLoadBalancerStatus", {
        "LoadBalancerId": slb_id,
        "LoadBalancerStatus": "active",
    })
    return [create_load_balancer_tcp_listener_res, add_backend_servers_res, set_load_balancer_status_res]


def main():
    parser = argparse.ArgumentParser(formatter_class=lambda prog: argparse.RawTextHelpFormatter(prog, width=200), description="""example:
  python3 ack.py -i ak -s sk -r cn-shanghai -a DescribeClusters
  python3 ack.py -i ak -s sk -r cn-shanghai -a DescribeClusterDetail --cluster-id cluster-id
  python3 ack.py -i ak -s sk -r cn-shanghai -a DescribeClusterResources --cluster-id cluster-id
  python3 ack.py -i ak -s sk -r cn-shanghai -a DescribeClusterUserKubeconfig --cluster-id cluster-id
  python3 ack.py -i ak -s sk -r cn-shanghai -a AddMasterToSlb --cluster-id cluster-id --slb-id slb-id --acl-id acl-id
""")
    parser.add_argument("-i", "--access-key-id", help="access key id")
    parser.add_argument("-s", "--access-key-secret", help="access key secret")
    parser.add_argument("-c", "--credential", help="credential file")
    parser.add_argument("-k", "--key-id", help="key id")
    parser.add_argument("-r", "--region-id", help="region id")
    parser.add_argument("-a", "--action", help="action", choices=[
        "DescribeClusters", "DescribeClusterDetail", "DescribeClusterResources", "DescribeClusterUserKubeconfig",
        "AddMasterToSlb"
    ])
    parser.add_argument("--cluster-id", help="cluster id")
    parser.add_argument("--cluster-name", help="cluster name")
    parser.add_argument("--slb-id", help="slb id")
    parser.add_argument("--acl-id", help="acl id")
    args = parser.parse_args()
    if args.credential:
        args.access_key_id, args.access_key_secret = aksk.load_from_file(args.credential)
    config = open_api_models.Config(
        access_key_id=args.access_key_id,
        access_key_secret=args.access_key_secret,
        region_id=args.region_id,
    )

    if args.action == "DescribeClusters":
        print(json.dumps(describe_clusters(config)))
    elif args.action == "DescribeClusterDetail":
        print(json.dumps(describe_cluster_detail(config, args.cluster_id, args.cluster_name)))
    elif args.action == "DescribeClusterResources":
        print(json.dumps(describe_cluster_resources(config, args.cluster_id, args.cluster_name)))
    elif args.action == "AddMasterToSlb":
        print(json.dumps(add_master_to_slb(config, args.region_id, args.cluster_id, args.cluster_name, args.slb_id, args.acl_id)))
    elif args.action == "DescribeClusterUserKubeconfig":
        print(json.dumps(describe_cluster_user_kubeconfig(config, args.cluster_id)))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
