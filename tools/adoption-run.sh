#!/usr/bin/env bash
# Run a wrapper adoption's validation on one host (docs/propagation.md, step 3).
#
# Usage: bash tools/adoption-run.sh [--only <name>[,<name>...]] <wrapper-checkout> <old-tag> <new-tag>
#
# Reference-only: run it from this checkout on the operator's host, after the
# wrapper checkout has adopted <new-tag>. It runs the commands that
# `tools/propagate.py --checklist` prints for that range, in order:
# - preflight: the checkout's commit, versions, free space and the images the
#   commands need; a missing image or less than 1 GiB free runs no command;
# - preparation: the engine image, rebuilt from the checkout when the tag
#   changes its inputs, with its ID and capability label recorded;
# - entries: the host unit tests (on the host's Python 3.11 or later, else in
#   the runtime image) and the runner modes, each with its full log, even
#   after an earlier failure.
# The logs, the image lists and a summary go to a new directory
# ~/sbx-logs-<wrapper>-<tag>-<host>-<time>, packed into <directory>.tar.gz.
# --only runs the preflight, the preparation and only the named entries.
# The exit status is zero only when every entry passed and no test skipped
# because an image was not prepared.
#
# It never commits, switches branches, fetches, pushes, removes images or
# containers, or changes the checkout; besides its logs, archive and private
# temporary directory it only rebuilds the engine image tag.
#
# Test-only variables: SANDBOX_ADOPTION_REFERENCE (the reference checkout that
# tools/propagate.py reads, through its --reference option),
# SANDBOX_ADOPTION_HOST_PYTHON (the Python of the host unit tests) and
# SANDBOX_ADOPTION_MIN_FREE_KIB (the free space floor).
set -Euo pipefail

here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
reference=${SANDBOX_ADOPTION_REFERENCE:-$(cd -- "$here/.." && pwd -P)}
min_free_kib=${SANDBOX_ADOPTION_MIN_FREE_KIB:-1048576}
host_python=${SANDBOX_ADOPTION_HOST_PYTHON:-python3}

usage() {
    printf 'Usage: bash tools/adoption-run.sh [--only <name>[,<name>...]] <wrapper-checkout> <old-tag> <new-tag>\n' >&2
    exit 2
}

only=''
case "${1:-}" in
    --only) (( $# >= 2 )) || usage; only=$2; shift 2 ;;
    --only=*) only=${1#--only=}; shift ;;
    -h|--help) usage ;;
esac
(( $# == 3 )) || usage
checkout=$(cd -- "$1" 2>/dev/null && pwd -P) || { printf 'adoption-run: no checkout at %s\n' "$1" >&2; exit 2; }
old=$2
new=$3

propagate=(python3 -I "$here/propagate.py" "$checkout" "$old" "$new" --checklist)
[[ -z "${SANDBOX_ADOPTION_REFERENCE:-}" ]] || propagate+=(--reference "$SANDBOX_ADOPTION_REFERENCE")
checklist=$("${propagate[@]}") || exit 1

kinds=()
names=()
commands=()
while IFS=$'\t' read -r kind name command; do
    [[ -n "$kind" ]] || continue
    kinds+=("$kind")
    names+=("$name")
    commands+=("$command")
done <<< "$checklist"

entry_names=()
for i in "${!kinds[@]}"; do
    [[ "${kinds[$i]}" == unit || "${kinds[$i]}" == mode ]] && entry_names+=("${names[$i]}")
done
selected=" ${entry_names[*]} "
if [[ -n "$only" ]]; then
    selected=' '
    IFS=',' read -ra wanted <<< "$only"
    for name in "${wanted[@]}"; do
        if [[ " ${entry_names[*]} " != *" $name "* ]]; then
            printf 'adoption-run: no checklist entry %s; the entries are: %s\n' "$name" "${entry_names[*]}" >&2
            exit 2
        fi
        selected+="$name "
    done
fi

host=$(hostname -s 2>/dev/null || printf '%s' "${HOSTNAME%%.*}")
base="$HOME/sbx-logs-$(basename -- "$checkout")-$new-$host-$(date +%Y%m%d-%H%M%S)"
logs=$base
count=1
while [[ -e "$logs" || -e "$logs.tar.gz" ]]; do
    count=$((count + 1))
    logs="$base-$count"
done
mkdir -- "$logs" || exit 1
summary="$logs/summary.txt"
note() {
    printf '%s\n' "$*" | tee -a "$summary"
}
printf '%s\n' "$checklist" > "$logs/checklist.txt"

image_of() {
    local i
    for i in "${!kinds[@]}"; do
        [[ "${kinds[$i]}" == image && "${names[$i]}" == "$1" ]] && printf '%s' "${commands[$i]}"
    done
    return 0
}

tags() {
    podman images --format '{{.Repository}}:{{.Tag}}' | sort > "$1"
}

finish() {
    podman images --format '{{.Repository}}:{{.Tag}} {{.ID}}' | sort > "$logs/images-after.txt" 2>&1
    note "result: $1"
    note "archive: $logs.tar.gz"
    tar -czf "$logs.tar.gz" -C "$(dirname -- "$logs")" "$(basename -- "$logs")"
    [[ "$1" == passed ]]
    exit $?
}

# Preflight.
{
    printf 'checkout: %s\n' "$checkout"
    git -C "$checkout" log -1 --format='commit: %H %d'
    git -C "$checkout" status --porcelain | sed 's/^/status: /'
    printf 'range: %s -> %s; only: %s\n' "$old" "$new" "${only:-all}"
    uname -srm
    podman version
    podman info --format 'cgroups: {{.Host.CgroupManager}} {{.Host.CgroupControllers}}; runtime: {{.Host.OCIRuntime.Name}} {{.Host.OCIRuntime.Version}}'
    df -Pk "$HOME" /tmp
    "$host_python" --version
} > "$logs/env.txt" 2>&1
podman images --format '{{.Repository}}:{{.Tag}} {{.ID}}' | sort > "$logs/images-before.txt" 2>&1
preflight=passed
for path in "$HOME" /tmp; do
    free=$(df -Pk -- "$path" | awk 'NR == 2 {print $4}')
    if [[ ! "$free" =~ ^[0-9]+$ ]] || (( free < min_free_kib )); then
        note "preflight: ${free:-unknown} KiB free in $path, below $min_free_kib KiB"
        preflight=failed
    fi
done
for i in "${!kinds[@]}"; do
    [[ "${kinds[$i]}" == image ]] || continue
    if ! podman image exists "${commands[$i]}"; then
        note "preflight: missing ${names[$i]} image ${commands[$i]}"
        preflight=failed
    fi
done
if [[ "$preflight" != passed ]]; then
    note 'preflight failed: no command run'
    finish failed
fi

# Preparation.
result=passed
for i in "${!kinds[@]}"; do
    [[ "${kinds[$i]}" == prepare ]] || continue
    read -ra words <<< "${commands[$i]}"
    (cd -- "$checkout" && "${words[@]}") > "$logs/prepare-${names[$i]}.log" 2>&1
    status=$?
    note "prepare ${names[$i]} exit=$status"
    (( status == 0 )) || result=failed
    if [[ "${names[$i]}" == engine && "${commands[$i]}" =~ --tag\ ([^ ]+) ]]; then
        note "engine image: $(podman image inspect --format '{{.Id}} label={{index .Labels "io.containers.capabilities"}}' \
            "${BASH_REMATCH[1]}" 2>&1)"
    fi
done

# Entries.
not_prepared=0
for i in "${!kinds[@]}"; do
    kind=${kinds[$i]}
    name=${names[$i]}
    if [[ "$kind" == manual ]]; then
        note "manual: ${commands[$i]}"
        continue
    fi
    [[ "$kind" == unit || "$kind" == mode ]] || continue
    [[ "$selected" == *" $name "* ]] || continue
    log="$logs/$name.log"
    read -ra words <<< "${commands[$i]}"
    where=''
    [[ "$name" != setup-runtime ]] || tags "$logs/tags-before.txt"
    if [[ "$kind" == unit ]]; then
        if "$host_python" -c 'import sys; sys.exit(sys.version_info < (3, 11))' 2>/dev/null; then
            private=$(mktemp -d "$HOME/.sbx-test-XXXXXX")
            where="host $("$host_python" --version 2>&1)"
            (cd -- "$checkout" && SANDBOX_TEST_TMPDIR="$private" "$host_python" "${words[@]:1}" -v) > "$log" 2>&1
            status=$?
            [[ "$private" == "$HOME"/.sbx-test-* ]] && rm -rf -- "$private"
        else
            runtime=$(image_of runtime)
            where="runtime image $runtime (host $("$host_python" --version 2>&1) is older than 3.11)"
            podman run --rm --network=none --userns=keep-id --user "$(id -u):$(id -g)" \
                --volume "$checkout:$checkout" --volume "$reference:$reference:ro" --workdir "$checkout" \
                --mount type=tmpfs,destination=/sandbox-test-tmp,tmpfs-mode=0700,U=true,tmpfs-size=1g \
                --env SANDBOX_TEST_TMPDIR=/sandbox-test-tmp --entrypoint python3 "$runtime" \
                "${words[@]:1}" -v > "$log" 2>&1
            status=$?
        fi
    else
        (cd -- "$checkout" && "${words[@]}") > "$log" 2>&1
        status=$?
    fi
    line=$(grep -E '^(OK|FAILED)' "$log" | tail -n 1)
    note "$name exit=$status ${line:-no result line}${where:+ ($where)}"
    (( status == 0 )) || result=failed
    if [[ "$name" == setup-runtime ]]; then
        tags "$logs/tags-after.txt"
        if diff "$logs/tags-before.txt" "$logs/tags-after.txt" > "$logs/tags-diff.txt"; then
            note 'setup-runtime tags: equal before and after'
        else
            note 'setup-runtime tags: different, see tags-diff.txt'
        fi
    fi
    while IFS=$'\t' read -r test reason; do
        [[ -n "$test" ]] || continue
        if [[ "$reason" == prepare\ * ]]; then
            note "  NOT PREPARED: $test: $reason"
            not_prepared=1
        else
            note "  skipped: $test: $reason"
        fi
    done < <(sed -nE "s/^ *(.*) \.\.\. skipped '(.*)'\$/\1\t\2/p" "$log")
done
(( not_prepared == 0 )) || result=failed
finish "$result"
