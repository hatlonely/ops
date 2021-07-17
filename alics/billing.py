#!/usr/bin/env python3

import argparse
import json
import pandas as pd


empty_tag = {
    "@user": "",
    "@tag": "",
    "@product": "",
    "@region": "",
    "@key": "",
    "@val": "",
}


def load_billing(filename):
    objs = []
    for line in open(filename):
        if not line.strip():
            continue
        objs.append(json.loads(line))
    return objs


def load_rule(filename):
    rules = {}
    fp = open(filename)
    for line in fp:
        kv = line.strip().split()
        if len(kv) != 6 or not kv[5]:
            continue
        product = kv[2]
        if product not in rules:
            rules[product] = []
        rules[product].append({
            "@user": kv[0],
            "@tag": kv[1],
            "@product": kv[2],
            "@region": kv[3],
            "@key": kv[4],
            "@val": kv[5],
        })
    fp.close()
    return rules


def merge(billings, rules):
    billings_out = []
    for billing in billings:
        billing["@timestamp"] = "{}T00:00:00".format(billing["BillingDate"])
        if billing["ProductCode"] not in rules:
            billings_out.append({**billing, **empty_tag})
            continue
        find = False
        for rule in rules[billing["ProductCode"]]:
            if rule["@val"] in billing[rule["@key"]]:
                if billing["ProductCode"] == "ecs":
                    if rule["@region"].startswith("cn") and rule["@region"] not in billing["Zone"]:
                        continue
                    if rule["@region"].startswith("ap-southeast") and not billing["Zone"].startswith("ap-southeast"):
                        continue
                    if rule["@region"].startswith("us-east") and not billing["Zone"].startswith("us-east"):
                        continue
                billings_out.append({**billing, **rule})
                find = True
                break
        if not find:
            billings_out.append({**billing, **empty_tag})
    return billings_out


def analyst(billings, keys="@user,@tag,@product,@region"):
    df = pd.DataFrame.from_records(billings)
    fields = [i.strip() for i in keys.split(",")]
    df = df[[*fields, "OutstandingAmount"]]
    df = df.groupby(fields, as_index=False).sum()
    df["OutstandingAmount"] = round(df["OutstandingAmount"], 2)
    return df


def main():
    parser = argparse.ArgumentParser(formatter_class=lambda prog: argparse.RawTextHelpFormatter(prog, width=200), description="""example:
      python3 billing_analyst.py --billing-file billings --rule-file rules
    """)
    parser.add_argument("--billing-file", required=True, help="billing file")
    parser.add_argument("--rule-file", required=True, help="rule file")
    parser.add_argument("--type", default="csv", help="type")
    parser.add_argument("--keys", default="@user,@tag,@product,@region", help="keys")
    parser.add_argument("--raw", type=bool, default=False, nargs='?', const=True, help="type")
    args = parser.parse_args()
    table = merge(load_billing(args.billing_file), load_rule(args.rule_file))
    if args.raw:
        for row in table:
            print(json.dumps(row))
        return
    df = analyst(table, args.keys)
    if args.type == "json":
        print(df.to_json(orient="records", lines=True))
    else:
        print(df.to_csv(encoding="utf-8", sep="\t", index=False))


if __name__ == "__main__":
    main()
