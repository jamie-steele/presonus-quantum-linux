/* SPDX-License-Identifier: MIT */
/* Reuse the hardware boundary shims, counters, and bounded deadline. */
#define ACP_SHIMS_ONLY
#include "discovery.c"

#include <spa/monitor/device.h>
#include <spa/support/loop.h>
#include <spa/support/plugin.h>

int main(int argc, char **argv)
{
    if (argc != 3 || access("/dev/snd", F_OK) == 0)
        return 10;
    void *private = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL);
    void *system = dlopen(argv[2], RTLD_NOW | RTLD_LOCAL);
    if (!private || !system) {
        fprintf(stderr, "dlopen: %s\n", dlerror());
        return 11;
    }
    spa_handle_factory_enum_func_t enumerate = dlsym(private, SPA_HANDLE_FACTORY_ENUM_FUNC_NAME);
    spa_handle_factory_enum_func_t original = dlsym(system, SPA_HANDLE_FACTORY_ENUM_FUNC_NAME);
    if (!enumerate || !original)
        return 12;

    struct spa_dict_item items[] = {
        { "device.vendor.id", "0x1c67" },
        { "device.product.id", "0x0104" },
        { "api.alsa.path", "hw:0" },
        { "api.alsa.use-ucm", "true" },
        { "api.acp.auto-profile", "false" },
        { "api.acp.auto-port", "false" },
        { "api.acp.disable-pro-audio", "true" },
        { "api.alsa.disable-mixer-path", "true" },
    };
    struct spa_dict info = SPA_DICT_INIT_ARRAY(items);
    struct spa_loop loop = { .iface = SPA_INTERFACE_INIT(SPA_TYPE_INTERFACE_Loop, 0, NULL, NULL) };
    struct spa_support support[] = { SPA_SUPPORT_INIT(SPA_TYPE_INTERFACE_Loop, &loop) };
    uint32_t index = 0;
    unsigned acp_factories = 0;
    const struct spa_handle_factory *factory;
    int result;

    signal(SIGALRM, deadline);
    alarm(3);
    while ((result = enumerate(&factory, &index)) > 0) {
        uint32_t original_index = index - 1;
        const struct spa_handle_factory *system_factory;
        if (original(&system_factory, &original_index) != 1)
            return 13;
        if (strcmp(factory->name, "api.alsa.acp.device") != 0) {
            if (factory != system_factory)
                return 14;
            continue;
        }
        acp_factories++;
        if (factory == system_factory)
            return 15;
        /* Missing PCI IDs must retain the distro factory's allocation. */
        if (spa_handle_factory_get_size(factory, NULL) !=
            spa_handle_factory_get_size(system_factory, NULL))
            return 16;
        struct spa_handle *handle = calloc(1, spa_handle_factory_get_size(factory, &info));
        if (!handle)
            return 17;
        if (spa_handle_factory_init(factory, handle, &info, support, 1) < 0)
            return 18;
        void *device;
        if (spa_handle_get_interface(handle, SPA_TYPE_INTERFACE_Device, &device) < 0)
            return 19;
        spa_handle_clear(handle);
        free(handle);
    }
    alarm(0);
    if (result < 0 || acp_factories != 1 || ucm_opens != 1 || pcm_opens != 39)
        return 20;
    /* Verify the package's SPA_PLUGIN_DIR also reaches this factory through
     * the actual distro PipeWire loader, rather than only direct dlopen. */
    void *pipewire = dlopen("libpipewire-0.3.so.0", RTLD_NOW | RTLD_LOCAL);
    if (!pipewire)
        return 21;
    void (*initialize)(int *, char ***) = dlsym(pipewire, "pw_init");
    struct spa_handle *(*load)(const char *, const char *, const struct spa_dict *,
                              uint32_t, const struct spa_support *) =
        dlsym(pipewire, "pw_load_spa_handle");
    int (*unload)(struct spa_handle *) = dlsym(pipewire, "pw_unload_spa_handle");
    void (*deinitialize)(void) = dlsym(pipewire, "pw_deinit");
    if (!initialize || !load || !unload || !deinitialize)
        return 22;
    initialize(NULL, NULL);
    alarm(3);
    struct spa_handle *loaded = load("alsa/libspa-alsa", "api.alsa.acp.device", &info, 1, support);
    if (!loaded)
        return 23;
    unload(loaded);
    alarm(0);
    deinitialize();
    if (ucm_opens != 2 || pcm_opens != 78)
        return 24;
    puts("PASS: packaged SPA factory discovers all 39 Quantum mappings; other factories use distro pointers.");
    return 0;
}
