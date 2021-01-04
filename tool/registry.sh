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

function CheckNotEmpty() {
    [ -n "$(eval echo "\$$1")" ] || Warn "$1 is empty"
}

function Push() {
    CheckNotEmpty "REGISTRY_USERNAME" || return 1
    CheckNotEmpty "REGISTRY_PASSWORD" || return 1
    CheckNotEmpty "REGISTRY_SERVER" || return 1
    CheckNotEmpty "REGISTRY_NAMESPACE" || return 1
    CheckNotEmpty "IMAGE_REPOSITORY" || return 1
    CheckNotEmpty "IMAGE_TAG" || return 1
    docker login --username="${REGISTRY_USERNAME}" --password="${REGISTRY_PASSWORD}" "${REGISTRY_SERVER}"
    docker tag "${REGISTRY_NAMESPACE}/${IMAGE_REPOSITORY}:${IMAGE_TAG}" "${REGISTRY_SERVER}/${REGISTRY_NAMESPACE}/${IMAGE_REPOSITORY}:${IMAGE_TAG}"
    docker push "${REGISTRY_SERVER}/${REGISTRY_NAMESPACE}/${IMAGE_REPOSITORY}:${IMAGE_TAG}"
}

function Help() {
    echo "sh registry.sh <action>"
    echo "example"
    echo "  sh registry.sh push"
}

function main() {
    if [ "$1" == "-h" ] || [ -z "$1" ]; then
        Help
        return 0
    fi

    action=$1

    case "${action}" in
        "push") Push;;
    esac
}

main "$@"
