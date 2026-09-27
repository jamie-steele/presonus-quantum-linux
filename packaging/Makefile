# The RFC's original Kbuild is shipped separately, without source edits.
KDIR ?= /lib/modules/$(shell uname -r)/build

all:
	$(MAKE) -C $(KDIR) M=$(CURDIR) CONFIG_SND_QUANTUM=m W=1 modules

clean:
	$(MAKE) -C $(KDIR) M=$(CURDIR) clean

.PHONY: all clean
