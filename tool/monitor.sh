#!/usr/bin/env bash

TMP=tmp

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

function FormatMemory() {
    awk '{
        hr[1024**2]="GB"; hr[1024]="MB";
            for (x=1024**3; x>=1024; x/=1024) {
                if ($1>=x) {
                    printf("%-.1f%-5s ", $1/x, hr[x]); break
                }
            }
        }
        { printf ("\t%-12s", $2) }
        { for ( x=3 ; x<=NF ; x++ ) { printf("\t%s",$x) } print ("") }
    '
}

function MemoryTop10() {
    local namespace=$1
    local pod_name=$2
    kubectl exec "${pod_name}" -n "${namespace}" -- ps --no-headers -eo rss,etime,command --sort -rss | head -10 | FormatMemory
}

function ProcessNumber() {
    local namespace=$1
    local pod_name=$2
    local process=$3
    number=$(kubectl exec "${pod_name}" -n "${namespace}" -- ps aux | grep -c "${process}")
    printf "%s\n" "$number"
}

function Help() {
    echo "sh monitor.sh <action> <pod_filter> [process]"
    echo "  action:     action"
    echo "  pod_filter: pod name filter keyword"
    echo "  process:    process name"
    echo "example"
    echo "  sh monitor.sh memory_top_10 editserver-webet-20200825043108-78675c7df5-r6229"
    echo "  sh monitor.sh process_number webet webet"
}

function main() {
    if [ -z "$2" ]; then
        Help
        return 0
    fi

    local action=$1
    local pod_filter=$2
    kubectl get pods -A -o wide | grep "${pod_filter}" | while read -r line; do
        namespace=$(echo "$line" | awk '{print $1}')
        pod_name=$(echo "$line" | awk '{print $2}')
        nodeip=$(echo "$line" | awk '{print $8}')
        etime=$(echo "$line" | awk '{print $6}')
        if [ -z "${pod_name}" ]; then
            Warn "pod not found"
            return 1
        fi
        case ${action} in
            "memory_top_10")
                value=$(MemoryTop10 "${namespace}" "${pod_name}")
                printf "%s\t%s\t%s\n" "${nodeip}" "${pod_name}" "${etime}"
                printf "%s\n" "${value}"
                ;;
            "process_number")
                local process=$3
                value=$(ProcessNumber "${namespace}" "${pod_name}" "${process}")
                printf "%s\t%s\t%s\t%s\n" "${nodeip}" "${pod_name}" "${etime}" "${value}"
                ;;
            *) Warn "action ${action} not found" && return 1
        esac
    done
}

main "$@"
