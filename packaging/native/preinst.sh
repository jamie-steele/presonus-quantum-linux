#!/bin/sh
# Runs before unpack: Depends (including Python) need not be configured yet.
set -eu

case "${1:-}" in
    install|upgrade) ;;
    *) exit 0 ;;
esac

check_parents() {
    parent=$1
    while [ "$parent" != / ]; do
        if [ -L "$parent" ]; then
            echo "Quantum migration stopped: symlink directory $parent" >&2
            exit 1
        fi
        parent=${parent%/*}
        [ -n "$parent" ] || parent=/
    done
}

backup=''
for path in \
    /usr/share/alsa/ucm2/P2626/P2626.conf \
    /usr/share/alsa/ucm2/P2626/HiFi.conf \
    /usr/share/alsa/ucm2/conf.d/snd-quantum/snd-quantum.conf \
    /usr/share/alsa/ucm2/conf.d/snd-quantum2626/snd-quantum2626.conf \
    /usr/share/wireplumber/main.lua.d/51-quantum2626.lua \
    /usr/share/wireplumber/wireplumber.conf.d/51-quantum2626.conf \
    /etc/modprobe.d/quantum2626-backend.conf; do
    if [ ! -e "$path" ] && [ ! -L "$path" ]; then
        continue
    fi
    check_parents "${path%/*}"
    if [ -L "$path" ] || [ ! -f "$path" ]; then
        echo "Quantum migration stopped: inspect non-regular profile $path" >&2
        exit 1
    fi
    if [ -z "$backup" ]; then
        check_parents /var/backups/quantum-migration
        mkdir -p /var/backups/quantum-migration
        backup=$(mktemp -d /var/backups/quantum-migration/preinstall.XXXXXXXX)
        chmod 700 "$backup"
        echo "Quantum pre-install backup: $backup"
    fi
    mkdir -p "$backup/files${path%/*}"
    cp -p "$path" "$backup/files$path"
    sha256sum "$path" >> "$backup/SHA256SUMS"
done

# A manual in-house install left a conffile that blocks the incoming backend.
# Move only the exact generated policy; custom and package-owned policies keep
# dpkg's ordinary conffile handling. All backup copies above completed first.
policy=/etc/modprobe.d/quantum2626-backend.conf
if [ -f "$policy" ] && [ "$(sha256sum "$policy" | cut -d ' ' -f 1)" = '@INHOUSE_SHA256@' ]; then
    if dpkg-query -S "$policy" >/dev/null 2>&1; then
        : # Package upgrades keep the conffile until post-configuration migration.
    else
        status=$?
        if [ "$status" -ne 1 ]; then
            echo 'Quantum migration stopped: cannot determine backend-policy ownership.' >&2
            exit 1
        fi
        rm -- "$policy"
    fi
fi
