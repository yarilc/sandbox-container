#!/bin/sh
# Serves the session engine's API (design D2): on loopback TCP in the session's
# network namespace for the session, and on the rootless default Unix socket
# for nested containers that mount it, such as tests/run-runtime.sh. The engine
# runs under --init, which reaps the services' children.
set -eu
port=${1:-2375}
case $port in
    ''|*[!0-9]*) echo 'usage: sandbox-engine [port]' >&2; exit 2 ;;
esac
socket=$XDG_RUNTIME_DIR/podman/podman.sock
mkdir -p -- "${socket%/*}"
podman system service --time=0 "unix://$socket" &
exec podman system service --time=0 "tcp://127.0.0.1:$port"
