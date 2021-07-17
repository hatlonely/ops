#!/usr/bin/env bash

function SyncImage() {
    local srcEndpoint=$1
    local srcNamespace=$2
    local srcUsername=$3
    local srcPassword=$4
    local tgtEndpoint=$5
    local tgtNamespace=$6
    local tgtUsername=$7
    local tgtPassword=$8
    local repository=$9
    local version=${10}

    if [[ -z "${srcUsername}" ]]; then
      docker pull "${srcEndpoint}/${srcNamespace}/${repository}:${version}"
    else
      docker login --username="${srcUsername}" --password="${srcPassword}" "${srcEndpoint}"
      docker pull "${srcEndpoint}/${srcNamespace}/${repository}:${version}"
      docker logout "${srcEndpoint}"
    fi

    docker login --username="${tgtUsername}" --password="${tgtPassword}" "${tgtEndpoint}"
    docker tag "${srcEndpoint}/${srcNamespace}/${repository}:${version}" "${tgtEndpoint}/${tgtNamespace}/${repository}:${version}"
    docker push "${tgtEndpoint}/${tgtNamespace}/${repository}:${version}"
    docker logout "${tgtEndpoint}"
}

function Help() {
    echo "sh image.sh <action> <srcEndpoint> <srcNamespace> <srcUsername> <srcPassword> <tgtEndpoint> <tgtNamespace> <tgtUsername> <tgtPassword> <repository> <version>"
    echo "example"
    echo "  sh image.sh sync \"quay.io\" \"prometheus\" \"\" \"\" \"registry.cn-shanghai.aliyuncs.com\" \"hatlonely\" \"hatlonely\" \"123456\" \"node-exporter\" \"v1.0.1\""
}

function main() {
    if [ "$1" == "-h" ] || [ -z "$1" ]; then
        Help
        return 0
    fi

    action=$1
    case "${action}" in
      "sync") SyncImage "$2" "$3" "$4" "$5" "$6" "$7" "$8" "$9" "${10}" "${11}"
    esac
}

main "$@"
