#!/usr/bin/env bash

set -eu

dockerd &

exec "$@"
