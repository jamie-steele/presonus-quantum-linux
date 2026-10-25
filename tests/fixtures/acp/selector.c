/* SPDX-License-Identifier: MIT */
#include <assert.h>
#include "../../../packaging/pipewire/plugin.c"

const struct spa_handle_factory spa_alsa_acp_device_factory = { .name = "patched" };

int main(void)
{
    const struct spa_handle_factory distro = { .name = "distro" };
    original_acp = &distro;
    assert(select_acp(NULL) == &distro);
    struct spa_dict_item items[] = {
        { "device.vendor.id", "0x1c67" },
        { "device.product.id", "0x0104" },
    };
    struct spa_dict info = SPA_DICT_INIT_ARRAY(items);
    assert(select_acp(&info) == &spa_alsa_acp_device_factory);
    items[0].value = "0x1234";
    assert(select_acp(&info) == &distro);
    items[0].value = "0x1c67";
    items[1].value = "0x1234";
    assert(select_acp(&info) == &distro);
    items[1].value = "0x0104";
    info.n_items = 1;
    assert(select_acp(&info) == &distro);
    return 0;
}
