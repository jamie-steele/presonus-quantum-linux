#!/usr/bin/env bash
set -Eeuo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
readonly script_dir
driver_dir=$(cd -- "$script_dir/.." && pwd)
readonly driver_dir
readonly lock_file="$driver_dir/upstream.lock"

usage() {
	cat >&2 <<'EOF'
usage: upstream-source.sh sync|verify|status

sync    download and verify the pinned patch into the external cache
verify  verify the cached source and Kbuild bridge without network access
status  report the pinned revision and local cache state
EOF
}

[[ -f "$lock_file" ]] || {
	echo "upstream lock is absent: $lock_file" >&2
	exit 1
}

# The lock is repository-owned input shared with Make; it contains only plain
# KEY=value assignments.
# shellcheck disable=SC1090
source "$lock_file"

: "${UPSTREAM_REVISION:?missing from upstream.lock}"
: "${UPSTREAM_LORE_URL:?missing from upstream.lock}"
: "${UPSTREAM_PATCH_URL:?missing from upstream.lock}"
: "${UPSTREAM_PATCH_SHA256:?missing from upstream.lock}"
: "${UPSTREAM_DECODED_PATCH_SHA256:?missing from upstream.lock}"
: "${UPSTREAM_SOURCE_TREE_SHA256:?missing from upstream.lock}"

readonly cache_root=${UPSTREAM_CACHE_ROOT:-${XDG_CACHE_HOME:-$HOME/.cache}/quantum2626/upstream}
readonly source_bridge="$driver_dir/.upstream-src"
cache_dir="$cache_root/$UPSTREAM_REVISION"
source_dir="$cache_dir/source"

resolve_bridged_source() {
	local bridged_main
	local bridged_quantum_dir
	local candidate_source

	[[ -L "$source_bridge/quantum_main.c" ]] || return
	bridged_main=$(readlink -f -- "$source_bridge/quantum_main.c")
	bridged_quantum_dir=$(dirname -- "$bridged_main")
	candidate_source=$(cd -- "$bridged_quantum_dir/../../.." && pwd)
	[[ -f "$candidate_source/sound/pci/quantum/quantum_main.c" ]] || return
	source_dir="$candidate_source"
	cache_dir=$(dirname -- "$source_dir")
}

source_tree_sha256() {
	(
		cd -- "$1"
		find sound/pci/quantum -type f \
			\( -name '*.c' -o -name '*.h' -o -name Kconfig -o -name Makefile \) \
			-print0 \
			| LC_ALL=C sort -z \
			| xargs -0 sha256sum \
			| sha256sum \
			| awk '{print $1}'
	)
}

verify_source() {
	local actual_tree_sha
	local receipt="$cache_dir/receipt"

	[[ -f "$source_dir/sound/pci/quantum/quantum_main.c" ]] || {
		echo "pinned upstream source is absent: $source_dir" >&2
		return 1
	}
	actual_tree_sha=$(source_tree_sha256 "$source_dir")
	[[ "$actual_tree_sha" == "$UPSTREAM_SOURCE_TREE_SHA256" ]] || {
		echo 'cached upstream source tree hash mismatch' >&2
		echo "expected: $UPSTREAM_SOURCE_TREE_SHA256" >&2
		echo "actual:   $actual_tree_sha" >&2
		return 1
	}
	[[ -f "$receipt" ]] || {
		echo "upstream cache receipt is absent: $receipt" >&2
		return 1
	}
	grep -Fqx "revision=$UPSTREAM_REVISION" "$receipt"
	grep -Fqx "patch_sha256=$UPSTREAM_PATCH_SHA256" "$receipt"
	grep -Fqx "decoded_patch_sha256=$UPSTREAM_DECODED_PATCH_SHA256" "$receipt"
	grep -Fqx "source_tree_sha256=$UPSTREAM_SOURCE_TREE_SHA256" "$receipt"
}

ensure_source_bridge() {
	local source_file
	local bridge_file

	if [[ -L "$source_bridge" ]]; then
		rm -- "$source_bridge"
	fi
	mkdir -p -- "$source_bridge"
	for source_file in "$source_dir"/sound/pci/quantum/*.c \
		"$source_dir"/sound/pci/quantum/*.h; do
		bridge_file="$source_bridge/$(basename -- "$source_file")"
		if [[ -e "$bridge_file" && ! -L "$bridge_file" ]]; then
			echo "refusing to replace non-symlink bridge file: $bridge_file" >&2
			return 1
		fi
		ln -sfn -- "$source_file" "$bridge_file"
	done
}

verify_bridge() {
	local source_file
	local bridge_file

	[[ -d "$source_bridge" && ! -L "$source_bridge" ]] || {
		echo "Kbuild source bridge is absent: $source_bridge" >&2
		return 1
	}
	for source_file in "$source_dir"/sound/pci/quantum/*.c \
		"$source_dir"/sound/pci/quantum/*.h; do
		bridge_file="$source_bridge/$(basename -- "$source_file")"
		[[ -L "$bridge_file" ]] || {
			echo "Kbuild source bridge file is absent: $bridge_file" >&2
			return 1
		}
		[[ $(readlink -f -- "$bridge_file") == $(readlink -f -- "$source_file") ]] || {
			echo "Kbuild source bridge targets the wrong revision: $bridge_file" >&2
			return 1
		}
	done
}

sync_source() {
	local temporary_dir=''
	local downloaded_patch
	local actual_patch_sha
	local actual_tree_sha

	if verify_source 2>/dev/null; then
		ensure_source_bridge
		echo "upstream source already verified: $source_dir"
		return
	fi
	if [[ -e "$cache_dir" ]]; then
		echo "refusing to replace invalid existing cache: $cache_dir" >&2
		exit 1
	fi

	mkdir -p -- "$cache_root"
	temporary_dir=$(mktemp -d "$cache_root/.${UPSTREAM_REVISION}.tmp.XXXXXX")
	trap 'if [[ -n ${temporary_dir:-} && -d $temporary_dir ]]; then rm -rf -- "$temporary_dir"; fi' EXIT
	downloaded_patch="$temporary_dir/upstream.patch"

	curl --fail --location --silent --show-error \
		"$UPSTREAM_PATCH_URL" -o "$downloaded_patch"
	actual_patch_sha=$(sha256sum "$downloaded_patch" | awk '{print $1}')
	[[ "$actual_patch_sha" == "$UPSTREAM_PATCH_SHA256" ]] || {
		echo 'downloaded upstream patch hash mismatch' >&2
		echo "expected: $UPSTREAM_PATCH_SHA256" >&2
		echo "actual:   $actual_patch_sha" >&2
		exit 1
	}

	mkdir -- "$temporary_dir/source"
	git -C "$temporary_dir/source" apply \
		--include='sound/pci/quantum/*' "$downloaded_patch"
	actual_tree_sha=$(source_tree_sha256 "$temporary_dir/source")
	[[ "$actual_tree_sha" == "$UPSTREAM_SOURCE_TREE_SHA256" ]] || {
		echo 'extracted upstream source tree hash mismatch' >&2
		echo "expected: $UPSTREAM_SOURCE_TREE_SHA256" >&2
		echo "actual:   $actual_tree_sha" >&2
		exit 1
	}

	printf '%s\n' \
		"revision=$UPSTREAM_REVISION" \
		"lore_url=$UPSTREAM_LORE_URL" \
		"patch_url=$UPSTREAM_PATCH_URL" \
		"patch_sha256=$UPSTREAM_PATCH_SHA256" \
		"decoded_patch_sha256=$UPSTREAM_DECODED_PATCH_SHA256" \
		"source_tree_sha256=$UPSTREAM_SOURCE_TREE_SHA256" \
		> "$temporary_dir/receipt"

	mv -- "$temporary_dir" "$cache_dir"
	temporary_dir=''
	trap - EXIT
	ensure_source_bridge
	verify_source
	echo "upstream source synchronized: $source_dir"
}

report_status() {
	echo "revision=$UPSTREAM_REVISION"
	echo "lore_url=$UPSTREAM_LORE_URL"
	echo "patch_sha256=$UPSTREAM_PATCH_SHA256"
	echo "decoded_patch_sha256=$UPSTREAM_DECODED_PATCH_SHA256"
	echo "source_tree_sha256=$UPSTREAM_SOURCE_TREE_SHA256"
	echo "cache_dir=$cache_dir"
	if verify_source 2>/dev/null && verify_bridge 2>/dev/null; then
		echo 'cache_status=verified'
	else
		echo 'cache_status=absent_or_invalid'
	fi
}

if [[ ${1:-} != sync ]]; then
	resolve_bridged_source
fi

case ${1:-} in
	sync)
		sync_source
		;;
	verify)
		verify_source
		verify_bridge
		echo "upstream source verified: $source_dir"
		;;
	status)
		report_status
		;;
	*)
		usage
		exit 2
		;;
esac
