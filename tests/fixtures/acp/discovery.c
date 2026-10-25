/* SPDX-License-Identifier: MIT */
#define _GNU_SOURCE
#include <alsa/asoundlib.h>
#include <alsa/use-case.h>
#include <dlfcn.h>
#include <errno.h>
#include <execinfo.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include "acp.h"

static unsigned pcm_opens;
static unsigned ucm_opens;

/* Replace only the hardware card lookup with the real virtual UCM parser. */
int snd_use_case_mgr_open(snd_use_case_mgr_t **manager, const char *name)
{
    int (*real_open)(snd_use_case_mgr_t **, const char *);
    real_open = dlsym(RTLD_NEXT, "snd_use_case_mgr_open");
    ucm_opens++;
    fprintf(stderr, "UCM lookup %s -> P2626\n", name);
    return real_open(manager, "P2626");
}

/* Keep ACP's real mappings/probes but substitute hardware PCM transport. */
int snd_pcm_open(snd_pcm_t **pcm, const char *name, snd_pcm_stream_t stream, int mode)
{
    int (*real_open)(snd_pcm_t **, const char *, snd_pcm_stream_t, int);
    real_open = dlsym(RTLD_NEXT, "snd_pcm_open");
    pcm_opens++;
    fprintf(stderr, "PCM probe %u: %s -> null\n", pcm_opens, name);
    return real_open(pcm, "null", stream, mode);
}

/* This test must never open a real control device. */
int snd_ctl_open(snd_ctl_t **ctl, const char *name, int mode)
{
    (void)ctl;
    (void)name;
    (void)mode;
    return -ENODEV;
}

int snd_ctl_open_lconf(snd_ctl_t **ctl, const char *name, int mode, snd_config_t *configuration)
{
    (void)configuration;
    return snd_ctl_open(ctl, name, mode);
}

int snd_card_get_index(const char *name)
{
    (void)name;
    return -ENODEV;
}

static void deadline(int signal_number)
{
    void *frames[30];
    (void)signal_number;
    int count = backtrace(frames, 30);
    dprintf(STDERR_FILENO, "DEADLINE ucm_opens=%u pcm_opens=%u\n", ucm_opens, pcm_opens);
    backtrace_symbols_fd(frames, count, STDERR_FILENO);
    _exit(124);
}

int main(void)
{
    struct acp_dict_item items[] = {
        { "api.alsa.use-ucm", "true" },
        { "api.acp.auto-profile", "false" },
        { "api.acp.auto-port", "false" },
        { "api.acp.disable-pro-audio", "true" },
        { "api.alsa.disable-mixer-path", "true" },
    };
    struct acp_dict properties = { .n_items = 5, .items = items };
    signal(SIGALRM, deadline);
    alarm(3);
    acp_set_log_level(4);
    struct acp_card *card = acp_card_new(0, &properties);
    if (!card) {
        perror("acp_card_new");
        return 1;
    }
    alarm(0);
    printf("ACP COMPLETE profiles=%u devices=%u ports=%u ucm_opens=%u pcm_opens=%u\n",
           card->n_profiles, card->n_devices, card->n_ports, ucm_opens, pcm_opens);
    for (unsigned index = 0; index < card->n_profiles; index++) {
        struct acp_card_profile *profile = card->profiles[index];
        printf("PROFILE\t%s", profile->name);
        for (unsigned device = 0; device < profile->n_devices; device++)
            printf("\t%s", profile->devices[device]->name);
        putchar('\n');
    }
    const char *expected_devices = getenv("ACP_TEST_DEVICES");
    const char *expected_profiles = getenv("ACP_TEST_PROFILES");
    unsigned devices = expected_devices ? strtoul(expected_devices, NULL, 10) : 39;
    unsigned profiles = expected_profiles ? strtoul(expected_profiles, NULL, 10) : 2;
    if (card->n_devices != devices || card->n_profiles != profiles ||
        card->n_ports != devices || ucm_opens != 1)
        return 2;
    if (devices == 39 && pcm_opens != 39)
        return 3;
    acp_card_destroy(card);
    return 0;
}
