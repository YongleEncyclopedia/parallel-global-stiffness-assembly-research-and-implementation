#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 || ( "$1" != "full" && "$1" != "presentation" ) ]]; then
    echo "错误：内部入口只接受 full 或 presentation。" >&2
    exit 2
fi

mode="$1"
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"

if command -v python3 >/dev/null 2>&1; then
    python_command="$(command -v python3)"
elif command -v python >/dev/null 2>&1; then
    python_command="$(command -v python)"
else
    echo "错误：没有找到 Python 3.10 或更高版本。" >&2
    exit 1
fi

if ! "$python_command" -c 'import struct,sys; raise SystemExit(0 if sys.version_info >= (3,10) and struct.calcsize("P") == 8 else 1)'; then
    echo "错误：需要 64 位 Python 3.10 或更高版本。" >&2
    exit 1
fi

export PYTHONIOENCODING=utf-8
exec "$python_command" "$script_dir/run_windhub.py" --mode "$mode"
