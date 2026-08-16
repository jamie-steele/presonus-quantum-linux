# Out-of-tree ALSA PCI driver for PreSonus Quantum 2626 (skeleton)
# Build: make -C /lib/modules/$(uname -r)/build M=$(PWD) modules
# Load:  sudo insmod snd-quantum2626.ko  (or modprobe after install)

obj-m := snd-quantum2626.o

KDIR ?= /lib/modules/$(shell uname -r)/build
PWD := $(shell pwd)
UCM2_DIR ?= /usr/share/alsa/ucm2
WIREPLUMBER_MAIN_LUA_DIR ?= /usr/share/wireplumber/main.lua.d

all:
	$(MAKE) -C $(KDIR) M=$(PWD) modules

clean:
	$(MAKE) -C $(KDIR) M=$(PWD) clean

install-module: all
	$(MAKE) -C $(KDIR) M=$(PWD) modules_install
	depmod -a

install-ucm:
	install -D -m 0644 ../alsa/ucm2/P2626/P2626.conf \
		$(DESTDIR)$(UCM2_DIR)/P2626/P2626.conf
	install -D -m 0644 ../alsa/ucm2/P2626/HiFi.conf \
		$(DESTDIR)$(UCM2_DIR)/P2626/HiFi.conf
	install -D -m 0644 \
		../alsa/ucm2/conf.d/snd-quantum2626/snd-quantum2626.conf \
		$(DESTDIR)$(UCM2_DIR)/conf.d/snd-quantum2626/snd-quantum2626.conf

install-wireplumber:
	install -D -m 0644 \
		../alsa/wireplumber/51-quantum2626.lua \
		$(DESTDIR)$(WIREPLUMBER_MAIN_LUA_DIR)/51-quantum2626.lua

install-audio: install-ucm install-wireplumber

install: install-module install-audio

.PHONY: all clean install install-module install-ucm install-wireplumber install-audio
