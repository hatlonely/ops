#!/usr/bin/env python3

import argparse
import json
import uuid
import aksk

from alibabacloud_batchcompute20181213 import client as bcsc
from alibabacloud_batchcompute20181213 import models as bcsm
from alibabacloud_tea_openapi import models as open_api_models


def list_clusters(client: bcsc.Client, project):
    marker = ""
    clusters = []
    while True:
        res = client.list_clusters(bcsm.ListClustersRequest(project=project, next_token=marker)).body
        for cluster in res.clusters:
            clusters.append(cluster.to_map())
        if res.next_token == "":
            break
        marker = res.next_token
    return clusters


def get_cluster(client: bcsc.Client, project, cluster_id, cluster_name):
    if cluster_id:
        res = client.get_cluster(bcsm.GetClusterRequest(project=project, cluster_id=cluster_id)).body
        return res.to_map()
    res = list_clusters(client, project)
    for cls in res:
        if cls["Name"] == cluster_name:
            return cls
    return None


def get_project(client: bcsc.Client, project):
    req = bcsm.GetProjectRequest()
    req.project = project
    res = client.get_project(req).body
    return res.to_map()


def create_project(client: bcsc.Client, project):
    req = bcsm.CreateProjectRequest()
    req.project = project
    definition = bcsm.ProjectDefinition()
    req.definition = definition
    res = client.create_project(req).body
    return res.to_map()


def del_cluster(client: bcsc.Client, project, cluster_id, cluster_name):
    if cluster_id:
        res = client.delete_cluster(bcsm.DeleteClusterRequest(project=project, cluster_id=cluster_id)).body
        return json.loads(json.dumps(res.to_map()))
    res = get_cluster(client, project, None, cluster_name)
    res = client.delete_cluster(bcsm.DeleteClusterRequest(project=project, cluster_id=res["ClusterId"])).body
    return json.loads(json.dumps(res.to_map()))


def create_cluster(client: bcsc.Client, project, cluster_desc_str):
    req = bcsm.CreateClusterRequest().from_map(json.loads(cluster_desc_str))
    res = get_cluster(client, project, None, req.name)
    if res:
        return res
    res = client.create_cluster(req).body
    return res.to_map()

def update_cluster(client: bcsc.Client, project, cluster_id, image_id, vm_count, change):
        request = bcsm.GetClusterRequest()
        request.project = project
        request.cluster_id = cluster_id
        cluster = client.get_cluster(request).body
        print("cur image:",cluster.definition.bootstrap.runtimes.docker.image)
        print("cur count:",cluster.definition.scaling.min_worker_count)

        definition = cluster.definition
        if image_id:
            definition.bootstrap.runtimes.docker.image = image_id
        if vm_count:
            definition.scaling.min_worker_count = int(vm_count)
        print("new image:",definition.bootstrap.runtimes.docker.image)
        print("new count:",definition.scaling.min_worker_count)

        if change == "true":
            request = bcsm.UpdateClusterRequest()
            request.project = project
            request.cluster_id = cluster_id
            request.definition = definition

            res = client.update_cluster(request).body
            return res.to_map()
        return {}

def main():
    parser = argparse.ArgumentParser(formatter_class=lambda prog: argparse.RawTextHelpFormatter(prog, width=200), description="""example:
  python3 bc2.py -c ~/.aksk/imm-dev -r cn-shanghai -u 1335926999564873 -p imm-dev -a GetProject
  python3 bc2.py -c ~/.aksk/imm-dev -r cn-shanghai -u 1335926999564873 -p imm-dev -a ListClusters
  python3 bc2.py -c ~/.aksk/imm-dev -r cn-shanghai -u 1335926999564873 -p imm-dev -a GetCluster --cluster-id cls-0udghyr5mICEYOcbkXtTuqDPF6B
  python3 bc2.py -c ~/.aksk/imm-dev -r cn-shanghai -u 1335926999564873 -p imm-dev -a GetCluster --cluster-name IMM_DEV_BC2_CONVERT_WPS_default_20201208
  python3 bc2.py -c ~/.aksk/imm-dev -r cn-shanghai -u 1335926999564873 -p imm-dev -a DelCluster --cluster-id cls-0udghyr5mICEYOcbkXtTuqDPF6B
  python3 bc2.py -c ~/.aksk/imm-dev -r cn-shanghai -u 1335926999564873 -p imm-dev -a CreateCluster --cluster-desc "$(cat ${TMP}/create_cluster.json)
  python3 bc2.py -c ~/.aksk/imm-dev -r cn-shanghai -u 1335926999564873 -p imm-dev -a UpdateCluster --cluster-id cls-0udghyr5mICEYOcbkXtTuqDPF6B --image-id registry-vpc.cn-shanghai.aliyuncs.com/imm-dev/transcode:0.1 --vm-count 20 --change true
""")
    parser.add_argument("-u", "--uid", help="user owner id")
    parser.add_argument("-p", "--project", help="project")
    parser.add_argument("-i", "--access-key-id", help="access key id")
    parser.add_argument("-s", "--access-key-secret", help="access key secret")
    parser.add_argument("-c", "--credential", help="credential file")
    parser.add_argument("-r", "--region-id", help="region id")
    parser.add_argument("-a", "--action", help="action", choices=[
        "ListClusters", "GetCluster", "DelCluster", "CreateCluster",
        "CreateProject", "GetProject", "UpdateCluster"
    ])
    parser.add_argument("--cluster-id", help="cluster id")
    parser.add_argument("--cluster-name", help="cluster name")
    parser.add_argument("--cluster-desc", help="cluster desc")
    parser.add_argument("--version", help="version")
    parser.add_argument("--vm-count", help="vm count")
    parser.add_argument("--image-id", help="image id")
    parser.add_argument("--change", help="change")
    parser.add_argument("--instance-type", default="ecs.sn2.medium", help="instance type")
    args = parser.parse_args()
    if args.credential:
        args.access_key_id, args.access_key_secret = aksk.load_from_file(args.credential)

    client = bcsc.Client(open_api_models.Config(
        access_key_id=args.access_key_id,
        access_key_secret=args.access_key_secret,
        endpoint="{}.{}.batchcompute.aliyuncs.com".format(args.uid, args.region_id),
        region_id=args.region_id,
        protocol="http",
        type="access_key"
    ))
    if args.action == "ListClusters":
        print(json.dumps(list_clusters(client, args.project)))
    elif args.action == "GetCluster":
        print(json.dumps(get_cluster(client, args.project, args.cluster_id, args.cluster_name)))
    elif args.action == "DelCluster":
        print(json.dumps(del_cluster(client, args.project, args.cluster_id, args.cluster_name)))
    elif args.action == "CreateCluster":
        print(json.dumps(create_cluster(client, args.project, args.cluster_desc)))
    elif args.action == "CreateProject":
        print(json.dumps(create_project(client, args.project)))
    elif args.action == "GetProject":
        print(json.dumps(get_project(client, args.project)))
    elif args.action == "UpdateCluster":
            print(json.dumps(update_cluster(client, args.project, args.cluster_id, args.image_id, args.vm_count, args.change)))
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
