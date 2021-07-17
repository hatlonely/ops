#!/usr/bin/env python3

import argparse
import json
import uuid
import aksk

from batchcompute import Client
from batchcompute.resources import AppDescription
from batchcompute.resources import ClusterDescription
from batchcompute.resources import AppJobDescription
from batchcompute.core.exceptions import ClientError

Client.register_region("cn-north-2-gov-1", "batchcompute.cn-north-2-gov-1.aliyuncs.com")

app_wps_tpl = """
{{
  "Name": "{app_name}",
  "EnvVars": {{}},
  "Description": "",
  "CommandLine": "c:/wps/wps_startup.bat",
  "VM": {{
    "ECSImageId": "img-windows-vpc"
  }},
  "Daemonize": true,
  "InputParameters": {{
    "Action": {{
      "Type": "String"
    }},
    "RequestId": {{
      "Type": "String"
    }},
    "Parameters": {{
      "Type": "String"
    }}
  }},
  "OutputParameters": {{
    "Key": {{
      "Type": "String"
    }}
  }},
  "Config": {{
    "InstanceCount": {{
      "Default": 1,
      "Description": "",
      "Overwritable": true
    }},
    "ResourceType": {{
      "Default": "OnDemand",
      "Description": "",
      "Overwritable": true
    }},
    "DiskType": {{
      "Default": "ephemeral",
      "Description": "",
      "Overwritable": true
    }},
    "MaxRetryCount": {{
      "Default": 0,
      "Description": "",
      "Overwritable": true
    }},
    "Timeout": {{
      "Default": 86400,
      "Description": "",
      "Overwritable": true
    }},
    "MinDiskSize": {{
      "Default": 40,
      "Description": "",
      "Overwritable": true
    }},
    "InstanceType": {{
      "Default": "",
      "Description": "",
      "Overwritable": true
    }}
  }}
}}
"""

cluster_wps_tpl = """
{{
  "Name": "{cluster_name}",
  "Description": "{cluster_name} created by bc.py",
  "ImageId": "img-windows-vpc",
  "ScheduleType": "Push",
  "Bootstrap": "e:\\\\bootstrap.bat c:\\\\wps",
  "UserData": {{
    "AES_KEY": "bVL.$^E*9#I$Q7d&l*?UY$6W%L0Mk#q1"
  }},
  "Configs": {{
    "Networks": {{
      "VPC": {{
        "VpcId": "{vpc_id}",
        "CidrBlock": "10.240.0.0/12"
      }}
    }},
    "Disks": {{
      "SystemDisk": {{
        "Size": 40
      }}
    }},
    "Mounts": {{
      "Entries": [
        {{
          "Source": "{mount_entry_source}/{version}/",
          "WriteSupport": false,
          "Destination": "e:"
        }}
      ]
    }}
  }},
  "Groups": {{
    "workers": {{
      "DesiredVMCount": {vm_count},
      "ResourceType": "OnDemand",
      "InstanceType": "{instance_type}"
    }}
  }}
}}
"""

job_wps_tpl = """
{{
  "Name": "{name}",
  "Description": "{name} create by bc.py",
  "Type": "App",
  "App": {{
    "AppName": "{app_name}",
    "AppTraceId": "{trace_id}",
    "Inputs": {{
        "Action": "Convert",
        "Parameters": {parameters},
        "RequestId": "{request_id}"
    }},
    "Config": {{
        "Timeout": 600,
        "ClusterId": "{cluster_id}"
    }},
    "CredentialConfig": {{
        "ServiceRole": "AliyunBatchComputeDefaultRole"
    }}
  }},
  "AutoRelease": true
}}
"""


def get_app(client: Client, app_name):
    res = client.get_app(app_name)
    return json.loads(str(res))


def create_app(client: Client, app_desc_str):
    app_desc = AppDescription(json.loads(app_desc_str))
    try:
        res = get_app(client, app_desc.Name)
        return res
    except ClientError as e:
        if e.status != 404:
            raise e
    res = client.create_app(app_desc)
    return json.loads(str(res))


def create_app_wps(client: Client, app_name):
    return create_app(client, app_wps_tpl.format(app_name=app_name))


def list_clusters(client: Client):
    marker = ""
    clusters = []
    while True:
        res = client.list_clusters(marker, 100)
        for cluster in res.Items:
            clusters.append(json.loads(str(cluster)))
        if res.NextMarker == "":
            break
        marker = res.NextMarker
    return clusters


def get_cluster(client: Client, cluster_id, cluster_name):
    if cluster_id:
        res = client.get_cluster(cluster_id)
        return json.loads(str(res))
    res = list_clusters(client)
    for cls in res:
        if cls["Name"] == cluster_name:
            return cls
    return None


def list_cluster_instances(client: Client, cluster_id, group_id):
    marker = ""
    instances = []
    while True:
        res = client.list_cluster_instances(cluster_id, group_id, marker, 100)
        for instance in res.Items:
            instances.append(json.loads(str(instance)))
        if res.NextMarker == "":
            break
        marker = res.NextMarker
    return instances


def create_cluster(client: Client, cluster_desc_str):
    cluster_desc = ClusterDescription(json.loads(cluster_desc_str))
    res = get_cluster(client, None, cluster_desc.Name)
    if res:
        return res
    res = client.create_cluster(cluster_desc)
    return json.loads(str(res))


def create_cluster_wps(client: Client, cluster_name, vpc_id, mount_entry_source, version, vm_count, instance_type="ecs.sn2.medium"):
    return create_cluster(client, cluster_wps_tpl.format(
        cluster_name=cluster_name, vpc_id=vpc_id, mount_entry_source=mount_entry_source, version=version, vm_count=vm_count,
        instance_type=instance_type,
    ))


def create_job(client: Client, job_desc_str):
    print(job_desc_str)
    job_desc = AppJobDescription(json.loads(job_desc_str))
    res = client.create_job(job_desc)
    return json.loads(str(res))


def create_job_wps(client: Client, app_name, cluster_name, parameters, name="job_by_bc_py_{}".format(uuid.uuid4())):
    res = get_cluster(client, None, cluster_name)
    return create_job(client, job_wps_tpl.format(
        name=name, app_name=app_name, cluster_id=res["Id"], parameters=json.dumps(parameters),
        trace_id=uuid.uuid4(), request_id=uuid.uuid4()
    ))


def main():
    parser = argparse.ArgumentParser(formatter_class=lambda prog: argparse.RawTextHelpFormatter(prog, width=200), description="""example:
  python3 bc.py -c ~/.aksk/imm-dev -r cn-shanghai -a ListClusters | jq ".[] | \\"\\(.Id) \\(.Name)\\""
  python3 bc.py -c ~/.aksk/imm-dev -r cn-shanghai -a GetCluster --cluster-id cluster-id | jq ".Groups.workers | \\"\\(.ActualVMCount) \\(.InstanceType)\\""
  python3 bc.py -c ~/.aksk/imm-dev -r cn-shanghai -a GetCluster --cluster-name IMM_DEV_CLUSTER_CONVERT_WPS_default_20200408_hl | jq .
  python3 bc.py -c ~/.aksk/imm-dev -r cn-shanghai -a ListClusterInstances --cluster-id cluster-id --group-id group-id
  python3 bc.py -c ~/.aksk/imm-dev -r cn-shanghai -a GetApp --app-name IMM_DEV_APP_CONVERT_WPS_default_20200520_regression
  python3 bc.py -c ~/.aksk/imm-dev -r cn-shanghai -a CreateAppWPS --app-name IMM_DEV_APP_CONVERT_WPS_default_20200920_hl
  python3 bc.py -c ~/.aksk/imm-dev -r cn-shanghai -a CreateClusterWPS \\
    --cluster-name IMM_DEV_CLUSTER_CONVERT_WPS_default_20200920_hl \\
    --vpc-id=vpc-id \\
    --mount-entry-source=oss://imm-dev-cn-shanghai/zyb/pkgs/CONVERT/WPS/ \\
    --version=20200520 \\
    --vm-count=1
  python3 bc.py -c ~/.aksk/imm-dev -r cn-shanghai -a CreateJobWPS \\
    --app-name IMM_DEV_APP_CONVERT_WPS_default_20200520_hl \\
    --cluster-name IMM_DEV_CLUSTER_CONVERT_WPS_default_20200520_hl \\
    --parameters "{
  \\"TgtType\\": \\"vector\\",
  \\"TgtUri\\": \\"oss://imm-dev-hl-shanghai/1.docx/imm/vector\\",
  \\"SrcUri\\": \\"oss://imm-dev-hl-shanghai/1.docx\\",
  \\"StartPage\\": 1,
  \\"EndPage\\": 200,
  \\"MaxSheetRow\\": 1000,
  \\"MaxSheetCol\\": 100
}"
""")
    parser.add_argument("-i", "--access-key-id", help="access key id")
    parser.add_argument("-s", "--access-key-secret", help="access key secret")
    parser.add_argument("-c", "--credential", help="credential file")
    parser.add_argument("-r", "--region-id", help="region id")
    parser.add_argument("-a", "--action", help="action", choices=[
        "ListClusters", "GetCluster", "ListClusterInstances", "GetApp",
        "CreateApp", "CreateAppWPS", "CreateCluster", "CreateClusterWPS",
        "CreateJobWPS"
    ])
    parser.add_argument("--cluster-id", help="cluster id")
    parser.add_argument("--group-id", help="group id")
    parser.add_argument("--app-name", help="app name")
    parser.add_argument("--app-desc", help="app desc")
    parser.add_argument("--cluster-name", help="cluster name")
    parser.add_argument("--cluster-desc", help="cluster desc")
    parser.add_argument("--vpc-id", help="vpc id")
    parser.add_argument("--mount-entry-source", help="mount entry source")
    parser.add_argument("--version", help="version")
    parser.add_argument("--vm-count", help="vm count")
    parser.add_argument("--parameters", help="parameters")
    parser.add_argument("--instance-type", default="ecs.sn2.medium", help="instance type")
    args = parser.parse_args()
    if args.credential:
        args.access_key_id, args.access_key_secret = aksk.load_from_file(args.credential)
    client = Client("batchcompute.{}.aliyuncs.com".format(args.region_id), args.access_key_id, args.access_key_secret)
    if args.action == "ListClusters":
        print(json.dumps(list_clusters(client)))
    elif args.action == "GetCluster":
        print(json.dumps(get_cluster(client, args.cluster_id, args.cluster_name)))
    elif args.action == "ListClusterInstances":
        print(json.dumps(list_cluster_instances(client, args.cluster_id, args.group_id)))
    elif args.action == "GetApp":
        print(json.dumps(get_app(client, args.app_name)))
    elif args.action == "CreateApp":
        print(json.dumps(create_app(client, args.app_desc)))
    elif args.action == "CreateCluster":
        print(json.dumps(create_cluster(client, args.cluster_desc)))
    elif args.action == "CreateAppWPS":
        print(json.dumps(create_app_wps(client, args.app_name)))
    elif args.action == "CreateClusterWPS":
        print(json.dumps((create_cluster_wps(client, args.cluster_name, args.vpc_id, args.mount_entry_source, args.version, args.vm_count, args.instance_type))))
    elif args.action == "CreateJobWPS":
        print(json.dumps(create_job_wps(client, args.app_name, args.cluster_name, args.parameters)))
    else:
        parser.print_help()


if __name__ == '__main__':
    main()