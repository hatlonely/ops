#!/usr/bin/env bash

function Trac() {
    echo "[TRAC] [$(date +"%Y-%m-%d %H:%M:%S")] $1"
}

function Info() {
    echo "\033[1;32m[INFO] [$(date +"%Y-%m-%d %H:%M:%S")] $1\033[0m"
}

function Warn() {
    echo "\033[1;31m[WARN] [$(date +"%Y-%m-%d %H:%M:%S")] $1\033[0m"
    return 1
}

function GetLogStore() {
    local ak="$1"
    local sk="$2"
    local endpoint="$3"
    local project="$4"
    local logstore="$5"
    local prefix="$6"
    mkdir -p "${prefix}"

    aliyunlog log get_index_config --project_name="${project}" --logstore_name="${logstore}" \
      --access-id="${ak}" --access-key="${sk}" --region-endpoint="${endpoint}" | jq . >"${prefix}/${logstore}.index.json"; test "${PIPESTATUS[0]}" -eq 0 &&
    Info "get index ${project} ${logstore} success" ||
    Warn "get index ${project} ${logstore} failed"
    aliyunlog log get_logtail_config --project_name="${project}" --config_name="${logstore}" \
      --access-id="${ak}" --access-key="${sk}" --region-endpoint="${endpoint}" | jq . >"${prefix}/${logstore}.logtail.json"; test "${PIPESTATUS[0]}" -eq 0 &&
    Info "get logtail ${project} ${logstore} success" ||
    Warn "get logtail ${project} ${logstore} failed"
}

function GetDashboard() {
    local ak="$1"
    local sk="$2"
    local endpoint="$3"
    local project="$4"
    local dashboard="$5"
    local prefix="$6"
    mkdir -p "${prefix}"

    dashboard_id=$(
      aliyunlog log list_dashboard --access-id="${ak}" --access-key="${sk}" --region-endpoint="${endpoint}" --project="${project}" | \
      jq -r ".dashboardItems[] | select(.displayName==\"${dashboard}\") | .dashboardName"
    )
    if [ -z "${dashboard_id}" ]; then
      Warn "dashboard ${dashboard} not found"
      return 1
    fi

    aliyunlog log get_dashboard --access-id="${ak}" --access-key="${sk}" --region-endpoint="${endpoint}" --project="${project}" --entity="${dashboard_id}" | \
      jq . >"${prefix}/${dashboard}.json"; test "${PIPESTATUS[0]}" -eq 0 &&
    Info "get dashboard ${project} ${dashboard} success" ||
    Warn "get dashboard ${project} ${dashboard} failed"
}

function GetAlert() {
    local ak="$1"
    local sk="$2"
    local endpoint="$3"
    local project="$4"
    local alert="$5"
    local prefix="$6"
    mkdir -p "${prefix}"

    alert_id=$(
      aliyunlog log list_alert --access-id="${ak}" --access-key="${sk}" --region-endpoint="${endpoint}" --project="${project}" | \
        jq -r ".results[] | select(.name==\"${alert}\") | .name"
    )
    if [ -z "${alert_id}" ]; then
      Warn "alert ${alert} not found"
      return 1
    fi

    aliyunlog log get_alert --access-id="${ak}" --access-key="${sk}" --region-endpoint="${endpoint}" --project="${project}" --entity="${alert_id}" | \
      jq >"${prefix}/${alert}.json"; test "${PIPESTATUS[0]}" -eq 0 &&
    Info "get alert ${project} ${alert} success" ||
    Warn "get alert ${project} ${alert} failed"
}

function PutLogStore() {
    local ak="$1"
    local sk="$2"
    local endpoint="$3"
    local project="$4"
    local logstore="$5"
    local prefix="$6"
    local machine_group="$7"

    aliyunlog log get_logstore --access-id="${ak}" --access-key="${sk}" --region-endpoint="${endpoint}" --project_name="${project}" --logstore_name="${logstore}" || {
        aliyunlog log create_logstore --access-id="${ak}" --access-key="${sk}" --region-endpoint="${endpoint}" --project_name="${project}" --logstore_name="${logstore}" &&
        Info "create logstore ${project} ${logstore} success" || {
            Warn "create logstore ${project} ${logstore} failed"
            return 1
        }
    }

    aliyunlog log get_index_config --project_name="${project}" --logstore_name="${logstore}" --access-id="${ak}" --access-key="${sk}" --region-endpoint="${endpoint}" && {
        aliyunlog log update_index --access-id="${ak}" --access-key="${sk}" --region-endpoint="${endpoint}" --project_name="${project}" --logstore_name="${logstore}" \
            --index_detail="file://./${prefix}/${logstore}.index.json" &&
        Info "update index ${project} ${logstore} success" ||
        Warn "update index ${project} ${logstore} failed"
    } || {
        aliyunlog log create_index --access-id="${ak}" --access-key="${sk}" --region-endpoint="${endpoint}" --project_name="${project}" --logstore_name="${logstore}" \
            --index_detail="file://./${prefix}/${logstore}.index.json" &&
        Info "create index ${project} ${logstore} success" ||
        Warn "create index ${project} ${logstore} failed"
    }

    aliyunlog log get_logtail_config --project_name="${project}" --config_name="${logstore}" --access-id="${ak}" --access-key="${sk}" --region-endpoint="${endpoint}" && {
        aliyunlog log update_logtail_config --access-id="${ak}" --access-key="${sk}" --region-endpoint="${endpoint}" --project_name="${project}" \
            --config_detail="file://./${prefix}/${logstore}.logtail.json" &&
        Info "update logtail ${project} ${logstore} success" ||
        Warn "update logtail ${project} ${logstore} failed"
    } || {
        aliyunlog log create_logtail_config --access-id="${ak}" --access-key="${sk}" --region-endpoint="${endpoint}" --project_name="${project}" \
            --config_detail="file://./${prefix}/${logstore}.logtail.json" &&
        Info "create logtail ${project} ${logstore} success" ||
        Warn "create logtail ${project} ${logstore} failed"
    }

    aliyunlog log apply_config_to_machine_group --access-id="${ak}" --access-key="${sk}" --region-endpoint="${endpoint}" --project_name="${project}" --config_name="${logstore}" --group_name="${machine_group}" &&
    Info "apply machine group ${project} ${logstore} ${machine_group} success" ||
    Warn "apply machine group ${project} ${logstore} ${machine_group} failed"
}

function PutDashboard() {
    local ak="$1"
    local sk="$2"
    local endpoint="$3"
    local project="$4"
    local dashboard="$5"
    local prefix="$6"

    dashboard_id=$(jq -r .dashboardName "${prefix}/${dashboard}.json")
    if [ -z "${dashboard_id}" ]; then
      Warn "dashboardName not found in ${prefix}/${dashboard}.json"
      return 1
    fi

    aliyunlog log get_dashboard --access-id="${ak}" --access-key="${sk}" --region-endpoint="${endpoint}" --project="${project}" --entity="${dashboard_id}" && {
        aliyunlog log update_dashboard --access-id="${ak}" --access-key="${sk}" --region-endpoint="${endpoint}" --project="${project}" --detail="file://./${prefix}/${dashboard}.json" &&
        Info "update dashboard ${project} ${dashboard} success" ||
        Warn "update dashboard ${project} ${dashboard} failed"
    } || {
        aliyunlog log create_dashboard --access-id="${ak}" --access-key="${sk}" --region-endpoint="${endpoint}" --project="${project}" --detail="file://./${prefix}/${dashboard}.json" &&
        Info "create dashboard ${project} ${dashboard} success" ||
        Warn "create dashboard ${project} ${dashboard} failed"
    }
}

function PutAlert() {
    local ak="$1"
    local sk="$2"
    local endpoint="$3"
    local project="$4"
    local alert="$5"
    local prefix="$6"

    alert_id=$(jq -r .name "${prefix}/${alert}.json")
    if [ -z "${alert_id}" ]; then
      Warn "dashboardName not found in ${prefix}/${alert}.json"
      return 1
    fi

    aliyunlog log get_alert --access-id="${ak}" --access-key="${sk}" --region-endpoint="${endpoint}" --project="${project}" --entity="${alert_id}" && {
        aliyunlog log update_alert --access-id="${ak}" --access-key="${sk}" --region-endpoint="${endpoint}" --project="${project}" --detail="file://./${prefix}/${alert}.json" &&
        Info "update alert ${project} ${alert} success" ||
        Warn "update alert ${project} ${alert} failed"
    } || {
        aliyunlog log create_alert --access-id="${ak}" --access-key="${sk}" --region-endpoint="${endpoint}" --project="${project}" --detail="file://./${prefix}/${alert}.json" &&
        Info "update alert ${project} ${alert} success" ||
        Warn "update alert ${project} ${alert} failed"
    }
}

function GetLogs() {
    local ak="$1"
    local sk="$2"
    local endpoint="$3"
    local project="$4"
    local logstore="$5"
    local from="$6"
    local to="$7"
    local query="$8"
    local offset="$9"
    local limit="${10}"

    if [ -z "${offset}" ]; then
        offset="0"
    fi
    if [ -z "${limit}" ]; then
        limit="100"
    fi

    aliyunlog log get_logs --access-id="${ak}" --access-key="${sk}" --region-endpoint="${endpoint}" --request="{
        \"topic\": \"\",
        \"project\": \"${project}\",
        \"logstore\": \"${logstore}\",
        \"fromTime\": \"${from}\",
        \"toTime\": \"${to}\",
        \"offset\": \"${offset}\",
        \"query\": \"${query}\",
        \"line\": \"${limit}\",
        \"reverse\": \"true\"
    }"
}

function Help() {
    echo "sh sls.sh <action> <ak> <sk> <region> <project> <resource> <prefix> [machine_group]"
    echo "example"
    echo "  sh sls.sh GetLogStore ak sk region project logstore prefix"
    echo "  sh sls.sh GetDashboard ak sk region project dashboard prefix"
    echo "  sh sls.sh GetAlert ak sk region project alert prefix"
    echo "  sh sls.sh PutLogStore ak sk region project logstore prefix machine_group"
    echo "  sh sls.sh PutDashboard ak sk region project logstore prefix"
    echo "  sh sls.sh PutAlert ak sk region project logstore prefix"
    echo "  sh sls.sh GetLogs ak sk region logstore from to query offset limit"
}

function main() {
    if [ "$1" == "-h" ] || [ -z "$1" ]; then
        Help
        return 0
    fi

    action=$1
    shift
    if [[ ! "$3" =~ .*log\.aliyuncs\.com ]] && [[ ! "$3" =~ .*sls\.aliyuncs\.com ]] && [[ ! "$3" =~ .*log\.aliyun-inc\.com ]]; then
        set -- "${@:1:2}" "$3.log.aliyuncs.com" "${@:4}"
    fi

    case "${action}" in
        "GetLogStore") GetLogStore "$@";;
        "GetDashboard") GetDashboard "$@";;
        "GetAlert") GetAlert "$@";;
        "PutLogStore") PutLogStore "$@";;
        "PutDashboard") PutDashboard "$@";;
        "PutAlert") PutAlert "$@";;
        "GetLogs") GetLogs "$@";;
    esac
}

main "$@"
