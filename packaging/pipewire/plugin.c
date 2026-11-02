/* SPDX-License-Identifier: MIT */
#include <dlfcn.h>
#include <errno.h>
#include <pthread.h>
#include <string.h>

#include <spa/support/plugin.h>
#include <spa/support/log.h>

extern const struct spa_handle_factory spa_alsa_acp_device_factory;
SPA_LOG_TOPIC_DEFINE(alsa_log_topic, "spa.alsa.quantum");
SPA_LOG_TOPIC_ENUM_DEFINE_REGISTERED;

/* Keep all other cards and factories on the installed distro implementation. */
static pthread_once_t original_once = PTHREAD_ONCE_INIT;
static spa_handle_factory_enum_func_t original_enum;
static const struct spa_handle_factory *original_acp;
static struct spa_handle_factory quantum_router;
static void *original_library;

static const struct spa_handle_factory *select_acp(const struct spa_dict *info)
{
    const char *vendor = info ? spa_dict_lookup(info, "device.vendor.id") : NULL;
    const char *product = info ? spa_dict_lookup(info, "device.product.id") : NULL;

    if (vendor && product && strcmp(vendor, "0x1c67") == 0 && strcmp(product, "0x0104") == 0)
        return &spa_alsa_acp_device_factory;
    return original_acp;
}

static size_t router_size(const struct spa_handle_factory *factory, const struct spa_dict *info)
{
    (void)factory;
    return spa_handle_factory_get_size(select_acp(info), info);
}

static int router_init(const struct spa_handle_factory *factory, struct spa_handle *handle,
                       const struct spa_dict *info, const struct spa_support *support,
                       uint32_t n_support)
{
    (void)factory;
    return spa_handle_factory_init(select_acp(info), handle, info, support, n_support);
}

static void load_original(void)
{
    const char *paths[] = {
        "/usr/lib/x86_64-linux-gnu/spa-0.2/alsa/libspa-alsa.so",
        "/usr/lib64/spa-0.2/alsa/libspa-alsa.so",
        "/usr/lib/spa-0.2/alsa/libspa-alsa.so",
    };

    for (size_t index = 0; index < sizeof(paths) / sizeof(paths[0]); index++) {
        original_library = dlopen(paths[index], RTLD_NOW | RTLD_LOCAL);
        if (original_library)
            break;
    }
    if (!original_library)
        return;

    original_enum = dlsym(original_library, SPA_HANDLE_FACTORY_ENUM_FUNC_NAME);
    if (!original_enum)
        return;

    uint32_t index = 0;
    const struct spa_handle_factory *factory;
    while (original_enum(&factory, &index) > 0) {
        if (strcmp(factory->name, "api.alsa.acp.device") == 0) {
            original_acp = factory;
            quantum_router = *factory;
            quantum_router.get_size = router_size;
            quantum_router.init = router_init;
            break;
        }
    }
}

SPA_EXPORT
int spa_handle_factory_enum(const struct spa_handle_factory **factory, uint32_t *index)
{
    if (!factory || !index)
        return -EINVAL;
    pthread_once(&original_once, load_original);
    if (!original_enum || !original_acp)
        return -ENOENT;

    int result = original_enum(factory, index);
    if (result > 0 && strcmp((*factory)->name, "api.alsa.acp.device") == 0)
        *factory = &quantum_router;
    return result;
}
