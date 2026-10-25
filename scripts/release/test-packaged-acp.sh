#!/usr/bin/env bash
# Exercise the installed package through the runtime SPA factory in a container.
set -Eeuo pipefail
[[ -f /.dockerenv || -f /run/.containerenv ]] || exit 1
[[ ! -e /dev/snd ]] || { echo 'Sound devices must not be available.' >&2; exit 1; }
work=$(mktemp -d /tmp/quantum-packaged-acp.XXXXXXXX)
archive=${1:-/usr/share/doc/quantum-dkms/acp/source/pipewire-1.6.2.tar.gz}
tar -xzf "$archive" -C "$work"
source="$work/pipewire-1.6.2"
cc -Wall -Wextra -Werror -D_GNU_SOURCE -I"$source/spa/include" \
    /workspace/tests/fixtures/acp/selector.c -ldl -pthread -o "$work/selector"
"$work/selector"
plugin=/usr/lib/quantum-dkms/spa-0.2/alsa/libspa-alsa.so
system=''
for candidate in /usr/lib/x86_64-linux-gnu/spa-0.2/alsa/libspa-alsa.so \
                 /usr/lib64/spa-0.2/alsa/libspa-alsa.so /usr/lib/spa-0.2/alsa/libspa-alsa.so; do
    if [[ -f "$candidate" ]]; then
        system=$candidate
        break
    fi
done
[[ -n "$system" && -f "$plugin" ]]
cc -Wall -Wextra -Werror -g -O1 -rdynamic \
    -I"$source/spa/include" -I"$source/spa/plugins/alsa/acp" \
    /workspace/tests/fixtures/acp/packaged.c \
    -Wl,--no-as-needed -lasound -ldl -o "$work/discovery"
printf 'pcm.null { type null }\n' > "$work/asound.conf"
# A private UCM tree retains distro include files but uses the installed payload.
cp -a /usr/share/alsa/ucm2 "$work/ucm2"
# Read the exact environment installed by the package's systemd drop-in.
plugin_path=$(sed -n 's/^Environment="SPA_PLUGIN_DIR=\(.*\)"$/\1/p' \
    /usr/lib/systemd/user/wireplumber.service.d/51-quantum-acp.conf)
[[ -n "$plugin_path" ]]
SPA_PLUGIN_DIR="$plugin_path" ALSA_CONFIG_PATH="$work/asound.conf" ALSA_CONFIG_UCM2="$work/ucm2" \
    timeout 8 "$work/discovery" "$plugin" "$system"
