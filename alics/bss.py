#!/usr/bin/env python3

import argparse
import json
import aksk
import datetime
import time

from aliyunsdkcore.client import AcsClient
from aliyunsdkbssopenapi.request.v20171214.QueryBillOverviewRequest import QueryBillOverviewRequest
from aliyunsdkbssopenapi.request.v20171214.DescribeInstanceBillRequest import DescribeInstanceBillRequest


def query_bill_overview(client, billing_cycle=(datetime.datetime.now() - datetime.timedelta(days=40)).strftime("%Y-%m"), billing_date=None):
    req = QueryBillOverviewRequest()
    req.set_accept_format('json')
    req.set_BillingCycle(billing_cycle)
    if billing_date:
        req.set_BillingDate(billing_date)
        req.set_Granularity("DAILY")
    res = client.do_action_with_exception(req)
    return json.loads(str(res, encoding='utf-8'))["Data"]["Items"]["Item"]


def describe_instance_bill(client, billing_cycle=(datetime.datetime.now() - datetime.timedelta(days=40)).strftime("%Y-%m"), billing_date=None):
    req = DescribeInstanceBillRequest()
    req.set_accept_format('json')
    req.set_BillingCycle(billing_cycle)
    req.set_MaxResults(300)
    if billing_date:
        req.set_BillingDate(billing_date)
        req.set_Granularity("DAILY")
    retry_times = 0
    items = []
    while True:
        res = client.do_action_with_exception(req)
        res = json.loads(str(res, encoding='utf-8'))
        if "Data" not in res:
            if retry_times >= 20:
                raise
            time.sleep(2 * retry_times + 5)
            retry_times += 1
            continue
        for item in res["Data"]["Items"]:
            items.append(item)
        if len(items) >= res["Data"]["TotalCount"]:
            break
        req.set_NextToken(res["Data"]["NextToken"])
        time.sleep(0.5)
        retry_times = 0
    return items


def main():
    parser = argparse.ArgumentParser(formatter_class=lambda prog: argparse.RawTextHelpFormatter(prog, width=200), description="""example:
  python3 bss.py -i ak -s sk -r cn-shanghai -a QueryBillOverview --billing-cycle 2020-06
  python3 bss.py -i ak -s sk -r cn-shanghai -a QueryInstanceBill --billing-cycle 2020-06
  python3 bss.py -i ak -s sk -r cn-shanghai -a QueryInstanceBill --billing-date 2020-07-10
  python3 bss.py -i ak -s sk -r cn-shanghai -a QueryInstanceBill --billing-date 2020-09-15 | jq '.[] | select(.ProductCode=="imm")'
""")
    parser.add_argument("-i", "--access-key-id", help="access key id")
    parser.add_argument("-s", "--access-key-secret", help="access key secret")
    parser.add_argument("-r", "--region-id", help="region id")
    parser.add_argument("-a", "--action", help="action", choices=[
        "QueryBillOverview", "QueryInstanceBill", "DescribeInstanceBill"])
    parser.add_argument("-c", "--credential", help="credential file")
    parser.add_argument("--billing-cycle", default=(datetime.datetime.now() - datetime.timedelta(days=40)).strftime("%Y-%m"), help="billing cycle")
    parser.add_argument("--billing-date", help="billing date")
    args = parser.parse_args()
    if args.credential:
        args.access_key_id, args.access_key_secret = aksk.load_from_file(args.credential)
    client = AcsClient(args.access_key_id, args.access_key_secret, args.region_id)
    if args.billing_date:
        args.billing_cycle = args.billing_date[:7]
    if args.action == "QueryBillOverview":
        print(json.dumps(query_bill_overview(client, args.billing_cycle, args.billing_date)))
    elif args.action == "DescribeInstanceBill":
        print(json.dumps(describe_instance_bill(client, args.billing_cycle, args.billing_date)))
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
