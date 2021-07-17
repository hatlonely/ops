#!/usr/bin/env python3

import argparse
import json
import sys
import fnv
import tablestore
import base64
import aksk
import diff
import kms
from aliyunsdkcore.client import AcsClient


def list_table(client):
    res = client.list_table()
    return json.loads(json.dumps(res))


def create_table(client, table, meta):
    res = client.create_table(
        tablestore.TableMeta(
            table, [(i[0], i[1]) for i in meta]
        ),
        tablestore.TableOptions(time_to_live=-1, max_version=1),
        tablestore.ReservedThroughput(tablestore.CapacityUnit(0, 0))
    )
    return json.loads(json.dumps(res))


def describe_table(client, table):
    res = client.describe_table(table)
    return {
        "timeToLive": json.loads(json.dumps(res.table_options.time_to_live)),
        "maxVersion": json.loads(json.dumps(res.table_options.max_version)),
        "pks": json.loads(json.dumps(res.table_meta.schema_of_primary_key))
    }


def get_range(client, table):
    meta = client.describe_table(table)
    keys = [v[0] for v in meta.table_meta.schema_of_primary_key]

    start_primary_keys = []
    end_primary_keys = []

    for key in keys:
        start_primary_keys.append((key, tablestore.INF_MIN))
        end_primary_keys.append((key, tablestore.INF_MAX))

    all_rows = []
    while start_primary_keys is not None:
        _, start_primary_keys, rows, _ = client.get_range(
            table, tablestore.Direction.FORWARD,
            start_primary_keys, end_primary_keys, []
        )
        all_rows.extend(rows)

    res = []
    for row in all_rows:
        pkmap = {}
        colmap = {}
        for pk in row.primary_key:
            pkmap[pk[0]] = pk[1]
        for col in row.attribute_columns:
            colmap[col[0]] = col[1]
        res.append({
            "PrimaryKeys": pkmap,
            "Columns": colmap,
        })
    return res


def put_row(client, table, row, change=False):
    if not change:
        res = get_row(client, table, row["PrimaryKeys"])
        diff.color_diff(res, row)
        return False
    # 如果行不存在，插入新行
    # 如果行存在，覆盖当前行，row 中不存在的列会被删除，等效于删除整行，再插入整行
    meta = client.describe_table(table)
    keys = [v[0] for v in meta.table_meta.schema_of_primary_key]
    pks = []
    for key in keys:
        pks.append((key, row["PrimaryKeys"][key]))
    cols = []
    for col in row["Columns"]:
        cols.append((col, row["Columns"][col]))
    _, _ = client.put_row(table, tablestore.Row(pks, cols))
    return True


def update_row(client, table, row, change=False, view=True):
    if not change and view:
        res = get_row(client, table, row["PrimaryKeys"])
        to_delete_keys = []
        for col in res["Columns"]:
            if col not in row["Columns"]:
                to_delete_keys.append(col)
        for key in to_delete_keys:
            del (res["Columns"][key])
        diff.color_diff(res, row)
        return False
    if not change:
        return False
    # 如果行不存在，插入行
    # 如果行存在，修改或者新增 row 中的行，row 中不存在的列不变
    meta = client.describe_table(table)
    keys = [v[0] for v in meta.table_meta.schema_of_primary_key]
    pks = []
    for key in keys:
        pks.append((key, row["PrimaryKeys"][key]))
    cols = []
    for col in row["Columns"]:
        cols.append((col, row["Columns"][col]))
    _, _ = client.update_row(table, tablestore.Row(pks, {"PUT": cols}), tablestore.Condition(tablestore.RowExistenceExpectation.IGNORE))
    return True


def get_row(client, table, primary_key):
    meta = client.describe_table(table)
    keys = [v[0] for v in meta.table_meta.schema_of_primary_key]
    pks = []
    for key in keys:
        pks.append((key, primary_key[key]))
    _, row, _ = client.get_row(table, pks)
    if row is None:
        return None
    colmap = {}
    for col in row.attribute_columns:
        colmap[col[0]] = col[1]
    return {"PrimaryKeys": primary_key, "Columns": colmap}


def get_canary_deploy(client, table, primary_key, column):
    row = get_row(client, table, primary_key)
    canary_deploys = row["Columns"][column]
    return json.loads(canary_deploys)


def put_canary_deploy(client, table, primary_key, column, deploy, change=False):
    old_deploys = get_canary_deploy(client, table, primary_key, column)
    new_deploys = [deploy]
    od = None
    for old_deploy in old_deploys:
        if all([old_deploy[k] == deploy[k] for k in ["ObjectType", "ObjectId", "Provider", "Function"]]):
            od = old_deploy
            continue
        new_deploys.append(old_deploy)
    old_deploys.sort(key=lambda x: (x["ObjectType"], x["ObjectId"], x["Provider"], x["Function"]))
    new_deploys.sort(key=lambda x: (x["ObjectType"], x["ObjectId"], x["Provider"], x["Function"]))
    if not change:
        diff.color_diff(od, deploy)
    return update_row(client, table, {"PrimaryKeys": primary_key, "Columns": {column: json.dumps(new_deploys)}}, change, view=False)


def del_canary_deploy(client, table, primary_key, column, deploy, change=False):
    old_deploys = get_canary_deploy(client, table, primary_key, column)
    new_deploys = []
    for old_deploy in old_deploys:
        if all([old_deploy[k] == deploy[k] for k in ["ObjectType", "ObjectId", "Provider", "Function"]]):
            continue
        new_deploys.append(old_deploy)
    if len(old_deploys) == len(new_deploys):
        return "no canary deploy deleted"
    if not change:
        diff.color_diff(old_deploys, new_deploys)
    return update_row(client, table, {"PrimaryKeys": primary_key, "Columns": {column: json.dumps(new_deploys)}}, change, view=False)


def get_task(client, table, owner_id, project, task_id):
    suffix = "{:04X}".format(fnv.hash(task_id.encode(), algorithm=fnv.fnv_1a, bits=32) % 0x10000)
    upa = "{}:{}:{}:{}".format(owner_id, project, task_id.split('-')[0], suffix)
    return get_row(client, table, {"UPA": upa, "TaskID": task_id})


def get_configcenter(client, kms_client, table):
    res = {}
    for row in get_range(client, table):
        block = row["PrimaryKeys"]["Block"]
        section = row["PrimaryKeys"]["Section"]
        key = row["PrimaryKeys"]["Key"]
        val = row["Columns"]["Value"]
        if key.startswith("@"):
            key = key[1:]
            val = base64.b64decode(kms.decrypt(kms_client, val)["Plaintext"]).decode()
        res["{}_{}_{}".format(block, section, key)] = val
    return res


def get_configcenter_key(client, kms_client, table, pk):
    vs = pk.split("_")
    block = vs[0]
    section = vs[1]
    key = vs[2]
    res = get_row(client, table, {
        "Block": block,
        "Section": section,
        "Key": key
    })
    if not res:
        res = get_row(client, table, {
            "Block": block,
            "Section": section,
            "Key": "@{}".format(key)
        })
        return base64.b64decode(kms.decrypt(kms_client, res["Columns"]["Value"])["Plaintext"]).decode()
    return res["Columns"]["Value"]


def put_configcenter(client, table, config, change, kms_client, cmkey, encrypt):
    for pk in config:
        put_configcenter_key(client, table, pk, config[pk], change, kms_client, cmkey, encrypt)


def put_configcenter_key(client, table, pk, val, change, kms_client, cmkey, encrypt):
    vs = pk.split("_")
    block = vs[0]
    section = vs[1]
    key = vs[2]
    if encrypt:
        key = "@{}".format(key)
        val = kms.encrypt(kms_client, cmkey, base64.b64encode(val.encode()))["CiphertextBlob"]
    return put_row(client, table, {
        "PrimaryKeys": {
            "Block": block,
            "Section": section,
            "Key": key
        },
        "Columns": {
            "Value": val
        }
    }, change)


def str2bool(v):
    if isinstance(v, bool):
        return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')


def main():
    parser = argparse.ArgumentParser(formatter_class=lambda prog: argparse.RawTextHelpFormatter(prog, width=200), description="""example:
  python3 ots.py -c ~/.aksk/imm-dev -r cn-shanghai -d imm-dev-hl -a CreateTable -t yaconfig --meta '[
    ["Block", "STRING"],
    ["Section", "STRING"]
  ]'
  python3 ots.py -c ~/.aksk/imm-dev -r cn-shanghai -d imm-dev-hl -a DescribeTable -t yaconfig
  python3 ots.py -c ~/.aksk/imm-dev -r cn-shanghai -d imm-dev-hl -a ListTable
  python3 ots.py -c ~/.aksk/imm-dev -r cn-shanghai -d imm-dev-hl -t ImmTasks -a GetTask --owner 1023210024677934 --project imm-test-hl-doc-proj-shanghai --task formatconvert-00402572-d8e9-4750-ab88-ac3f388f63d1
  python3 ots.py -c ~/.aksk/imm-dev -r cn-shanghai -d imm-dev-hl -t IMMConfig -a GetRange > IMMConfig.json
  python3 ots.py -c ~/.aksk/imm-dev -r cn-shanghai -d imm-dev-hl -t IMMConfig -a GetRow --primary-keys '{"Block": "WebOfficeBilling", "Section": "SLS"}'
  python3 ots.py -c ~/.aksk/imm-dev -r cn-shanghai -d imm-dev-hl -t IMMConfig -a PutRow --rows '{"PrimaryKeys": {"Block": "WebOfficeBilling", "Section": "SLS"}, "Columns": {"Enable": true}}'
  python3 ots.py -c ~/.aksk/imm-dev -r cn-shanghai -d imm-dev-hl -t IMMConfig -a PutRow --primary-keys '{"Block": "WebOfficeBilling", "Section": "SLS"}' --column '{"Enable": false}'
  python3 ots.py -c ~/.aksk/imm-dev -r cn-shanghai -d imm-dev-hl -t IMMConfig -a UpdateRow --primary-keys '{"Block": "WebOfficeBilling", "Section": "SLS"}' --column '{"Enable": false}'
  python3 ots.py -c ~/.aksk/imm-dev -r cn-shanghai -d imm-dev-hl -t IMMConfig -a GetCanaryDeploy --primary-keys '{"Block": "Base", "Section": "Common"}' --column CanaryDeploy
  python3 ots.py -c ~/.aksk/imm-dev -r cn-shanghai -d imm-dev-regressi -t IMMConfig -a PutCanaryDeploy \\
      --primary-keys '{"Block": "Base", "Section": "Common"}' --column CanaryDeploy --deploy '{
    "ObjectType": "user",
    "ObjectId": "default",
    "Provider": "WPS",
    "Function": "CONVERT",
    "LatestVersion": {
      "SyncAppName": "IMM_DEV_APP_CONVERT_WPS_default_20200520_regression",
      "SyncClusterName": "IMM_DEV_CLUSTER_CONVERT_WPS_default_20200520_regression_sync",
      "AsyncAppName": "IMM_DEV_APP_CONVERT_WPS_default_20200923_regression",
      "AsyncClusterName": "IMM_DEV_CLUSTER_CONVERT_WPS_default_20200923_regression"
    },
    "CanaryDeployVersion": {
      "SyncAppName": "IMM_DEV_APP_CONVERT_WPS_default_20200520_regression",
      "SyncClusterName": "IMM_DEV_CLUSTER_CONVERT_WPS_default_20200520_regression_sync",
      "AsyncAppName": "IMM_DEV_APP_CONVERT_WPS_default_20200923_regression",
      "AsyncClusterName": "IMM_DEV_CLUSTER_CONVERT_WPS_default_20200923_regression"
    },
    "Percent": 100
  }'
  python3 ots.py -c ~/.aksk/imm-dev -r cn-shanghai -d imm-dev-hl -t IMMConfig -a DelCanaryDeploy \\
      --primary-keys '{"Block": "Base", "Section": "Common"}' --column CanaryDeploy --deploy '{
    "ObjectType": "user",
    "ObjectId": "default",
    "Provider": "WPS",
    "Function": "CONVERT"
  }'
  cat IMMConfig.json | python3 ots.py -c ~/.aksk/imm-dev -r cn-shanghai -d imm-dev-hl -t IMMConfig -a PutRow
  python3 ots.py -c ~/.aksk/imm-dev -r cn-shanghai -d configcenter -t config_imm_dev_hl -a GetConfigCenter
  python3 ots.py -c ~/.aksk/imm-dev -r cn-shanghai -d configcenter -t config_imm_dev_hl -a PutConfigCenter --config "$(cat 1.json)"
  python3 ots.py -c ~/.aksk/imm-dev -r cn-shanghai -d configcenter -t config_imm_dev_hl -a PutConfigCenter --config "$(cat 1.json)" --cmkey "xxx" --encrypt
  python3 ots.py -c ~/.aksk/imm-dev -r cn-shanghai -d configcenter -t config_imm_dev_hl -a GetConfigCenterByKey --key WebOffice_OSS_AK
  python3 ots.py -c ~/.aksk/imm-dev -r cn-shanghai -d configcenter -t config_imm_dev_hl -a PutConfigCenterByKey --key WebOffice_OSS_AK --value xxx --cmkey "xxx" --encrypt
""")
    parser.add_argument("-i", "--access-key-id", help="access key id")
    parser.add_argument("-s", "--access-key-secret", help="access key secret")
    parser.add_argument("-c", "--credential", help="credential file")
    parser.add_argument("-e", "--endpoint", help="endpoint")
    parser.add_argument("-r", "--region-id", help="region id")
    parser.add_argument("-d", "--instance", help="instance")
    parser.add_argument("-t", "--table", help="table")
    parser.add_argument("--rows", help="row json format")
    parser.add_argument("--primary-keys", help="primary keys json format")
    parser.add_argument("--columns", help="columns json format")
    parser.add_argument("--meta", help="table meta")
    parser.add_argument("--change", nargs="?", const=True, default=False, type=str2bool, help="change data")
    parser.add_argument("--column", help="column name")
    parser.add_argument("--deploy", help="canary deploy json format")
    parser.add_argument("--owner", type=str, help="owner id")
    parser.add_argument("--project", help="project")
    parser.add_argument("--task", help="task id")
    parser.add_argument("--key", help="configcenter key")
    parser.add_argument("--value", help="configcenter value")
    parser.add_argument("--cmkey", help="configcenter cmkey")
    parser.add_argument("--config", help="configcenter config")
    parser.add_argument("--encrypt", nargs="?", const=True, default=False, type=str2bool, help="configcenter config")
    parser.add_argument("-a", "--action", help="action", choices=[
        "ListTable", "GetRange", "PutRow", "UpdateRow", "GetRow", "CreateTable", "DescribeTable",
        "GetCanaryDeploy", "PutCanaryDeploy", "DelCanaryDeploy", "GetTask",
        "GetConfigCenter", "PutConfigCenter", "GetConfigCenterByKey", "PutConfigCenterByKey"
    ])
    args = parser.parse_args()
    if args.credential:
        args.access_key_id, args.access_key_secret = aksk.load_from_file(args.credential)
    if not args.endpoint:
        args.endpoint = "https://{}.{}.ots.aliyuncs.com".format(args.instance, args.region_id)
    client = tablestore.OTSClient(args.endpoint, args.access_key_id, args.access_key_secret, args.instance)
    kms_cli = AcsClient(args.access_key_id, args.access_key_secret, args.region_id)

    if args.action == "ListTable":
        print(json.dumps(list_table(client)))
    elif args.action == "GetRange":
        for row in get_range(client, args.table):
            print(json.dumps(row))
    elif args.action == "GetRow":
        row = get_row(client, args.table, json.loads(args.primary_keys))
        if row is not None:
            print(json.dumps(row))
    elif args.action == "UpdateRow":
        if args.rows:
            if args.rows[0] == "@":
                rows = json.load((open(args.rows[1:])))
            else:
                rows = json.loads(args.rows)
            if isinstance(rows, list):
                for row in rows:
                    print(json.dumps(update_row(client, args.table, row, args.change)))
            else:
                print(json.dumps(update_row(client, args.table, rows, args.change)))
        elif args.primary_keys and args.columns:
            print(json.dumps(update_row(client, args.table, {"PrimaryKeys": json.loads(args.primary_keys), "Columns": json.loads(args.columns)}, args.change)))
        else:
            for row in sys.stdin:
                print(json.dumps(update_row(client, args.table, json.loads(row))))
    elif args.action == "PutRow":
        if args.rows:
            if args.rows[0] == "@":
                rows = json.load((open(args.rows[1:])))
            else:
                rows = json.loads(args.rows)
            if isinstance(rows, list):
                for row in rows:
                    print(json.dumps(put_row(client, args.table, row, args.change)))
            else:
                print(json.dumps(put_row(client, args.table, rows, args.change)))
        elif args.primary_keys and args.columns:
            print(json.dumps(put_row(client, args.table, {"PrimaryKeys": json.loads(args.primary_keys), "Columns": json.loads(args.columns)}, args.change)))
        else:
            for row in sys.stdin:
                print(json.dumps(put_row(client, args.table, json.loads(row))))
    elif args.action == "GetCanaryDeploy":
        print(json.dumps(get_canary_deploy(client, args.table, json.loads(args.primary_keys), args.column)))
    elif args.action == "PutCanaryDeploy":
        print(json.dumps(put_canary_deploy(client, args.table, json.loads(args.primary_keys), args.column, json.loads(args.deploy), args.change)))
    elif args.action == "DelCanaryDeploy":
        print(json.dumps(del_canary_deploy(client, args.table, json.loads(args.primary_keys), args.column, json.loads(args.deploy), args.change)))
    elif args.action == "GetTask":
        print(json.dumps(get_task(client, args.table, args.owner, args.project, args.task)))
    elif args.action == "CreateTable":
        print(json.dumps(create_table(client, args.table, json.loads(args.meta))))
    elif args.action == "DescribeTable":
        print(json.dumps(describe_table(client, args.table)))
    elif args.action == "GetConfigCenter":
        print(json.dumps(get_configcenter(client, kms_cli, args.table)))
    elif args.action == "PutConfigCenter":
        print(json.dumps(put_configcenter(client, args.table, json.loads(args.config), args.change, kms_cli, args.cmkey, args.encrypt)))
    elif args.action == "GetConfigCenterByKey":
        print(json.dumps(get_configcenter_key(client, kms_cli, args.table, args.key)))
    elif args.action == "PutConfigCenterByKey":
        print(json.dumps(put_configcenter_key(client, args.table, args.key, args.value, args.change, kms_cli, args.cmkey, args.encrypt)))
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
