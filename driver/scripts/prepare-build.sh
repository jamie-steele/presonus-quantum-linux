#!/usr/bin/env bash
# Stage source links so older Kbuild versions also keep output outside driver/.
set -Eeuo pipefail
shopt -s nullglob

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
driver_dir=$(cd -- "$script_dir/.." && pwd)
backend=${1:?driver backend required}
build_dir=${2:?absolute build directory required}

case "$backend" in
    inhouse)
        source_dir="$driver_dir/inhouse"
        source_subdir=inhouse
        ;;
    upstream)
        source_dir="$driver_dir/.upstream-src"
        source_subdir=.upstream-src
        ;;
    *)
        echo "Unsupported driver backend: $backend" >&2
        exit 1
        ;;
esac

[[ "$build_dir" == /* ]] || {
    echo 'Build directory must be absolute.' >&2
    exit 1
}

source_files=("$source_dir"/*.[ch])
if (( ${#source_files[@]} == 0 )); then
    echo "Driver source files are absent: $source_dir" >&2
    exit 1
fi

link_source() {
    local source=$1
    local destination=$2

    if [[ -e "$destination" && ! -L "$destination" ]]; then
        echo "Refusing to replace a non-symlink build input: $destination" >&2
        return 1
    fi
    ln -sfn -- "$source" "$destination"
}

mkdir -p -- "$build_dir/$source_subdir"
link_source "$driver_dir/Kbuild" "$build_dir/Kbuild"
if [[ "$backend" == inhouse ]]; then
    link_source "$source_dir/Kbuild" "$build_dir/inhouse/Kbuild"
fi
for source_file in "${source_files[@]}"; do
    link_source "$source_file" "$build_dir/$source_subdir/$(basename -- "$source_file")"
done
