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
    client="$1"
    project="$2"
    logstore="$3"
    prefix="$4"
    mkdir -p "${prefix}"
    aliyunlog log get_index_config --project_name="${project}" --logstore_name="${logstore}" \
      --client-name="${client}" | jq . >"${prefix}/${logstore}.index.json"; test "${PIPESTATUS[0]}" -eq 0 &&
    Info "get index ${project} ${logstore} success" ||
    Warn "get index ${project} ${logstore} failed"
    aliyunlog log get_logtail_config --project_name="${project}" --config_name="${logstore}" \
      --client-name="${client}" | jq . >"${prefix}/${logstore}.logtail.json"; test "${PIPESTATUS[0]}" -eq 0 &&
    Info "get logtail ${project} ${logstore} success" ||
    Warn "get logtail ${project} ${logstore} failed"
}

function GetDashboard() {
    client="$1"
    project="$2"
    dashboard="$3"
    prefix="$4"
    mkdir -p "${prefix}"

    dashboard_id=$(
      aliyunlog log list_dashboard --client-name="${client}" --project="${project}" | \
      jq -r ".dashboardItems[] | select(.displayName==\"${dashboard}\") | .dashboardName"
    )
    if [ -z "${dashboard_id}" ]; then
      Warn "dashboard ${dashboard} not found"
      return 1
    fi

    aliyunlog log get_dashboard --client-name="${client}" --project="${project}" --entity="${dashboard_id}" | \
      jq . >"${prefix}/${dashboard}.json"; test "${PIPESTATUS[0]}" -eq 0 &&
    Info "get dashboard ${project} ${dashboard} success" ||
    Warn "get dashboard ${project} ${dashboard} failed"
}

function GetAlert() {
    client="$1"
    project="$2"
    alert="$3"
    prefix="$4"
    mkdir -p "${prefix}"

    alert_id=$(
      aliyunlog log list_alert --client-name="${client}" --project="${project}" | \
        jq -r ".results[] | select(.displayName==\"${alert}\") | .name"
    )
    if [ -z "${alert_id}" ]; then
      Warn "alert ${alert} not found"
      return 1
    fi

    aliyunlog log get_alert --client-name="${client}" --project="${project}" --entity="${alert_id}" | \
      jq >"${prefix}/${alert}.json"; test "${PIPESTATUS[0]}" -eq 0 &&
    Info "get alert ${project} ${alert} success" ||
    Warn "get alert ${project} ${alert} failed"
}

function PutLogStore() {
    client="$1"
    project="$2"
    logstore="$3"
    prefix="$4"
    machine_group="$5"
    aliyunlog log get_logstore --client-name="${client}" --project_name="${project}" --logstore_name="${logstore}" || {
        aliyunlog log create_logstore --client-name="${client}" --project_name="${project}" --logstore_name="${logstore}" &&
        Info "create logstore ${project} ${logstore} success" || {
            Warn "create logstore ${project} ${logstore} failed"
            return 1
        }
    }

    aliyunlog log get_index_config --project_name="${project}" --logstore_name="${logstore}" --client-name="${client}" && {
        aliyunlog log update_index --client-name="${client}" --project_name="${project}" --logstore_name="${logstore}" \
            --index_detail="file://./${prefix}/${logstore}.index.json" &&
        Info "update index ${project} ${logstore} success" ||
        Warn "update index ${project} ${logstore} failed"
    } || {
        aliyunlog log create_index --client-name="${client}" --project_name="${project}" --logstore_name="${logstore}" \
            --index_detail="file://./${prefix}/${logstore}.index.json" &&
        Info "create index ${project} ${logstore} success" ||
        Warn "create index ${project} ${logstore} failed"
    }

    aliyunlog log get_logtail_config --project_name="${project}" --config_name="${logstore}" --client-name="${client}" && {
        aliyunlog log update_logtail_config --client-name="${client}" --project_name="${project}" \
            --config_detail="file://./${prefix}/${logstore}.logtail.json" &&
        Info "update logtail ${project} ${logstore} success" ||
        Warn "update logtail ${project} ${logstore} failed"
    } || {
        aliyunlog log create_logtail_config --client-name="${client}" --project_name="${project}" \
            --config_detail="file://./${prefix}/${logstore}.logtail.json" &&
        Info "create logtail ${project} ${logstore} success" ||
        Warn "create logtail ${project} ${logstore} failed"
    }

    aliyunlog log apply_config_to_machine_group --client-name="${client}" --project_name="${project}" --config_name="${logstore}" --group_name="${machine_group}" &&
    Info "apply machine group ${project} ${logstore} ${machine_group} success" ||
    Warn "apply machine group ${project} ${logstore} ${machine_group} failed"
}

function PutDashboard() {
    client="$1"
    project="$2"
    dashboard="$3"
    prefix="$4"

    dashboard_id=$(jq -r .dashboardName "${prefix}/${dashboard}.json")
    if [ -z "${dashboard_id}" ]; then
      Warn "dashboardName not found in ${prefix}/${dashboard}.json"
      return 1
    fi

    aliyunlog log get_dashboard --client-name="${client}" --project="${project}" --entity="${dashboard_id}" && {
        aliyunlog log update_dashboard --client-name="${client}" --project="${project}" --detail="file://./${prefix}/${dashboard}.json" &&
        Info "update dashboard ${project} ${dashboard} success" ||
        Warn "update dashboard ${project} ${dashboard} failed"
    } || {
        aliyunlog log create_dashboard --client-name="${client}" --project="${project}" --detail="file://./${prefix}/${dashboard}.json" &&
        Info "create dashboard ${project} ${dashboard} success" ||
        Warn "create dashboard ${project} ${dashboard} failed"
    }
}

function PutAlert() {
    client="$1"
    project="$2"
    alert="$3"
    prefix="$4"

    alert_id=$(jq -r .name "${prefix}/${alert}.json")
    if [ -z "${alert_id}" ]; then
      Warn "dashboardName not found in ${prefix}/${alert}.json"
      return 1
    fi

    aliyunlog log get_alert --client-name="${client}" --project="${project}" --entity="${alert_id}" && {
        aliyunlog log update_alert --client-name="${client}" --project="${project}" --detail="file://./${prefix}/${alert}.json" &&
        Info "update alert ${project} ${alert} success" ||
        Warn "update alert ${project} ${alert} failed"
    } || {
        aliyunlog log create_alert --client-name="${client}" --project="${project}" --detail="file://./${prefix}/${alert}.json" &&
        Info "update alert ${project} ${alert} success" ||
        Warn "update alert ${project} ${alert} failed"
    }
}

function Help() {
    echo "sh sls.sh <action> <client> <project> <resource> <prefix> [machine_group]"
    echo "example"
    echo "  sh sls.sh GetLogStore client project logstore prefix"
    echo "  sh sls.sh PutLogStore client project logstore prefix machine_group"
    echo "  sh sls.sh GetDashboard client project dashboard prefix"
    echo "  sh sls.sh PutDashboard client project dashboard prefix"
    echo "  sh sls.sh GetAlert client project alert prefix"
    echo "  sh sls.sh PutAlert client project alert prefix"
}

function main() {
    if [ "$1" == "-h" ] || [ -z "$1" ]; then
        Help
        return 0
    fi

    action=$1

    case "${action}" in
        "GetLogStore") GetLogStore "$2" "$3" "$4" "$5";;
        "GetDashboard") GetDashboard "$2" "$3" "$4" "$5";;
        "GetAlert") GetAlert "$2" "$3" "$4" "$5";;
        "PutLogStore") PutLogStore "$2" "$3" "$4" "$5" "$6";;
        "PutDashboard") PutDashboard "$2" "$3" "$4" "$5";;
        "PutAlert") PutAlert "$2" "$3" "$4" "$5";;
    esac
}

main "$@"
