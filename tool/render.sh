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

function Render() {
    local in=$1
    local out=$2

    if [[ -f "${in}" ]]; then
        RenderFile "${in}" "${out}"
    elif [[ -d "${in}" ]]; then
        find "${in}" -type f | while read -r fin; do
            fout="${fin//$in/$out}"
            ext="${fin##*.}"
            if [[ "${ext}" == "tpl" ]]; then
                RenderFile "${fin}" "${fout%.*}"
            else
                mkdir -p "$(dirname "${fout}")"
                cp "${fin}" "${fout}"
            fi
        done
    else
        Warn "unsupported input file or not exist"
        return 1
    fi
}

function RenderFile() {
    local in=$1
    local out=$2

    CheckNotEmpty "in" || return 1
    CheckNotEmpty "out" || return 1

    [ ! -f "${in}" ] && {
        Warn "[${in}] no such file or directory"
        return 2
    }

    mkdir -p "$(dirname "${out}")"

    eval "cat > \"${out}\" <<EOF
$(< "${in}")
EOF"
}

function Help() {
    echo "sh render.sh <input> <output>"
    echo "example"
    echo "  sh render.sh values.yaml.tpl values.yaml"
}

function main() {
    if [ "$1" == "-h" ] || [ -z "$1" ]; then
        Help
        return 0
    fi

    Render "$1" "$2"
}

main "$@"
