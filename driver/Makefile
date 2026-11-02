# Out-of-tree ALSA PCI drivers for PreSonus Quantum 2626.
#
# The upstream RFC is the forward backend. Its pinned source is fetched into an
# external cache by the explicit upstream-sync target; normal builds never use
# the network. Select the locally developed fallback with:
#
#   make QUANTUM_DRIVER=inhouse

QUANTUM_DRIVER_ORIGIN := $(origin QUANTUM_DRIVER)
QUANTUM_DRIVER ?= upstream
QUANTUM_DRIVERS := inhouse upstream

include upstream.lock

UPSTREAM_CACHE_ROOT ?= $(if $(XDG_CACHE_HOME),$(XDG_CACHE_HOME),$(HOME)/.cache)/quantum2626/upstream
UPSTREAM_SOURCE_TOOL := scripts/upstream-source.sh
UPSTREAM_SOURCE_LINK := .upstream-src

ifeq ($(filter $(QUANTUM_DRIVER),$(QUANTUM_DRIVERS)),)
$(error QUANTUM_DRIVER must be one of: $(QUANTUM_DRIVERS))
endif

ifeq ($(QUANTUM_DRIVER),inhouse)
QUANTUM_MODULE := snd-quantum2626
else
ifneq ($(filter upstream-sync upstream-status clean inhouse check-backend-install \
	install-backend-selection install-ucm install-wireplumber install-audio,$(MAKECMDGOALS)),)
else ifeq ($(wildcard $(UPSTREAM_SOURCE_LINK)/quantum_main.c),)
$(error pinned upstream source is absent; run 'make -C driver upstream-sync')
endif
QUANTUM_MODULE := snd-quantum
endif

KDIR ?= /lib/modules/$(shell uname -r)/build
BUILD_ROOT ?= $(abspath ../build/driver)
BUILD_DIR := $(abspath $(BUILD_ROOT)/$(QUANTUM_DRIVER))
KERNEL_RELEASE ?= $(shell uname -r)
UCM2_DIR ?= /usr/share/alsa/ucm2
WIREPLUMBER_MAIN_LUA_DIR ?= /usr/share/wireplumber/main.lua.d
WIREPLUMBER_CONF_DIR ?= /usr/share/wireplumber/wireplumber.conf.d
WIREPLUMBER_SERIES ?= auto
MODPROBE_DIR ?= /etc/modprobe.d
INITRAMFS_TOOL ?= auto
BACKEND_CONFIG_SOURCE := modprobe.d/quantum2626-$(QUANTUM_DRIVER).conf
BACKEND_CONFIG_NAME := quantum2626-backend.conf

ifneq ($(filter install install-module install-backend-selection,$(MAKECMDGOALS)),)
ifeq ($(QUANTUM_DRIVER_ORIGIN),undefined)
$(error installation requires an explicit backend; use 'make install-upstream' or 'make install-inhouse')
endif
endif

ifeq ($(QUANTUM_DRIVER),upstream)
all: upstream-verify
endif

all:
	bash scripts/prepare-build.sh "$(QUANTUM_DRIVER)" "$(BUILD_DIR)"
	@echo "Building $(QUANTUM_DRIVER) backend ($(BUILD_DIR)/$(QUANTUM_MODULE).ko)"
	$(MAKE) -C "$(KDIR)" M="$(BUILD_DIR)" QUANTUM_DRIVER="$(QUANTUM_DRIVER)" modules

inhouse:
	$(MAKE) QUANTUM_DRIVER=inhouse all

upstream:
	$(MAKE) QUANTUM_DRIVER=upstream all

upstream-sync:
	UPSTREAM_CACHE_ROOT="$(UPSTREAM_CACHE_ROOT)" ./$(UPSTREAM_SOURCE_TOOL) sync

upstream-verify:
	UPSTREAM_CACHE_ROOT="$(UPSTREAM_CACHE_ROOT)" ./$(UPSTREAM_SOURCE_TOOL) verify

upstream-status:
	UPSTREAM_CACHE_ROOT="$(UPSTREAM_CACHE_ROOT)" ./$(UPSTREAM_SOURCE_TOOL) status

clean:
	@set -e; for backend in $(QUANTUM_DRIVERS); do \
		build_dir="$(abspath $(BUILD_ROOT))/$$backend"; \
		if test -d "$$build_dir"; then \
			$(MAKE) -C "$(KDIR)" M="$$build_dir" QUANTUM_DRIVER="$$backend" clean; \
		fi; \
	done

install-module: all
	$(MAKE) -C "$(KDIR)" M="$(BUILD_DIR)" QUANTUM_DRIVER="$(QUANTUM_DRIVER)" modules_install
	@if test -n "$(INSTALL_MOD_PATH)"; then \
		depmod -b "$(INSTALL_MOD_PATH)" -a "$(KERNEL_RELEASE)"; \
	else \
		depmod -a "$(KERNEL_RELEASE)"; \
	fi

check-backend-install:
	@test -f "$(BACKEND_CONFIG_SOURCE)"
	@if test -z "$(DESTDIR)"; then \
		INITRAMFS_TOOL="$(INITRAMFS_TOOL)" bash scripts/host-tools.sh check; \
	fi

install-backend-selection: check-backend-install
	install -D -m 0644 "$(BACKEND_CONFIG_SOURCE)" \
		"$(DESTDIR)$(MODPROBE_DIR)/$(BACKEND_CONFIG_NAME)"
	@if test -z "$(DESTDIR)"; then \
		INITRAMFS_TOOL="$(INITRAMFS_TOOL)" bash scripts/host-tools.sh refresh "$(KERNEL_RELEASE)"; \
	else \
		echo "Staged $(QUANTUM_DRIVER) boot selection; initramfs update skipped under DESTDIR"; \
	fi

install-ucm:
	install -D -m 0644 ../alsa/ucm2/P2626/P2626.conf \
		$(DESTDIR)$(UCM2_DIR)/P2626/P2626.conf
	install -D -m 0644 ../alsa/ucm2/P2626/HiFi.conf \
		$(DESTDIR)$(UCM2_DIR)/P2626/HiFi.conf
	install -D -m 0644 \
		../alsa/ucm2/conf.d/snd-quantum2626/snd-quantum2626.conf \
		$(DESTDIR)$(UCM2_DIR)/conf.d/snd-quantum2626/snd-quantum2626.conf
	install -D -m 0644 \
		../alsa/ucm2/conf.d/snd-quantum/snd-quantum.conf \
		$(DESTDIR)$(UCM2_DIR)/conf.d/snd-quantum/snd-quantum.conf

install-wireplumber:
	@series=$$(WIREPLUMBER_SERIES="$(WIREPLUMBER_SERIES)" bash scripts/host-tools.sh wireplumber); \
	case "$$series" in \
		0.4) install -D -m 0644 ../alsa/wireplumber/51-quantum2626.lua \
			"$(DESTDIR)$(WIREPLUMBER_MAIN_LUA_DIR)/51-quantum2626.lua" ;; \
		0.5) install -D -m 0644 ../alsa/wireplumber/51-quantum2626.conf \
			"$(DESTDIR)$(WIREPLUMBER_CONF_DIR)/51-quantum2626.conf" ;; \
		*) exit 1 ;; \
	esac

install-audio: install-ucm install-wireplumber

install:
	$(MAKE) QUANTUM_DRIVER="$(QUANTUM_DRIVER)" check-backend-install
	@WIREPLUMBER_SERIES="$(WIREPLUMBER_SERIES)" bash scripts/host-tools.sh wireplumber >/dev/null
	$(MAKE) QUANTUM_DRIVER="$(QUANTUM_DRIVER)" install-module
	$(MAKE) QUANTUM_DRIVER="$(QUANTUM_DRIVER)" install-audio
	$(MAKE) QUANTUM_DRIVER="$(QUANTUM_DRIVER)" install-backend-selection

install-upstream:
	$(MAKE) QUANTUM_DRIVER=upstream install

install-inhouse:
	$(MAKE) QUANTUM_DRIVER=inhouse install

.PHONY: all inhouse upstream upstream-sync upstream-verify upstream-status clean \
	check-backend-install install install-upstream install-inhouse install-module \
	install-backend-selection install-ucm install-wireplumber install-audio
