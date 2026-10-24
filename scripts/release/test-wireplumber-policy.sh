#!/usr/bin/env bash
# Called after native package installation in a disposable distro container.
set -Eeuo pipefail
[[ -f /.dockerenv || -f /run/.containerenv ]] || exit 1

# Deliberately select the other generation, then reinstall the real distro
# WirePlumber package. Its file trigger must restore the correct policy without
# invoking DKMS or restarting services from Quantum's trigger handler.
python3 -B - <<'PY'
import importlib.util
from pathlib import Path

path = Path('/usr/lib/quantum-dkms/wireplumber_policy.py')
specification = importlib.util.spec_from_file_location('policy', path)
policy = importlib.util.module_from_spec(specification)
specification.loader.exec_module(policy)
series = policy.installed_series()
policy.select_policy(Path('/'), '0.5' if series == '0.4' else '0.4')
PY

apt-get install -y --no-install-recommends --reinstall wireplumber
series=$(bash /workspace/driver/scripts/host-tools.sh wireplumber)
if [[ "$series" == 0.4 ]]; then
    test -L /usr/share/wireplumber/main.lua.d/51-quantum2626.lua
    test ! -e /usr/share/wireplumber/wireplumber.conf.d/51-quantum2626.conf
else
    test ! -e /usr/share/wireplumber/main.lua.d/51-quantum2626.lua
    test -L /usr/share/wireplumber/wireplumber.conf.d/51-quantum2626.conf
fi
echo "PASS: WirePlumber $series package reinstall reselected the correct policy through dpkg triggers."
