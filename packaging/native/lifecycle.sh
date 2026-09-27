# Included in native package scripts; no module loads or service restarts.
set -eu

refresh_boot_images() {
    for modules in /lib/modules/*; do
        [ -d "$modules" ] || continue
        kernel=${modules##*/}
        if command -v update-initramfs >/dev/null 2>&1; then
            [ -e "/boot/initrd.img-$kernel" ] || continue
            update-initramfs -u -k "$kernel"
        elif command -v dracut >/dev/null 2>&1; then
            if [ -e "/boot/initramfs-$kernel.img" ]; then
                dracut --force "/boot/initramfs-$kernel.img" "$kernel"
            elif [ -e "/boot/initrd-$kernel" ]; then
                dracut --force "/boot/initrd-$kernel" "$kernel"
            fi
        fi
    done
}

configure_module() {
    found_headers=false
    for modules in /lib/modules/*; do
        if [ -f "$modules/build/Makefile" ]; then
            found_headers=true
        fi
    done
    if [ "$found_headers" = false ]; then
        echo 'Install kernel headers/devel for your kernel, then reconfigure quantum-dkms.' >&2
        return 1
    fi
    if [ -z "$(dkms status -m quantum -v "$version")" ]; then
        dkms add -m quantum -v "$version"
    fi
    for modules in /lib/modules/*; do
        [ -f "$modules/build/Makefile" ] || continue
        kernel=${modules##*/}
        dkms build -m quantum -v "$version" -k "$kernel"
        # RFC modules are unversioned; a packaging upgrade must replace this
        # specific module even when its embedded MODULE_VERSION is unchanged.
        dkms install -m quantum -v "$version" -k "$kernel" --force
        depmod -a "$kernel"
    done
    refresh_boot_images
    echo 'Quantum installed for the next boot. No modules or audio services were restarted.'
}

remove_module() {
    if [ -n "$(dkms status -m quantum -v "$version")" ]; then
        dkms remove -m quantum -v "$version" --all
        for modules in /lib/modules/*; do
            [ -d "$modules" ] || continue
            depmod -a "${modules##*/}"
        done
    fi
}
