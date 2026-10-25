/* SPDX-License-Identifier: GPL-2.0-only */

#ifndef QUANTUM2626_RATES_H
#define QUANTUM2626_RATES_H

#include <linux/types.h>

#define QUANTUM_RATE_PROFILE_COUNT 6

struct quantum_rate_profile {
	unsigned int rate;
	unsigned int channels;
	u32 tci_value;
};

extern const struct quantum_rate_profile
quantum_rate_profiles[QUANTUM_RATE_PROFILE_COUNT];

const struct quantum_rate_profile *
quantum_rate_profile_for_rate(unsigned int rate);
unsigned int quantum_tci_decode_sample_rate(u32 value);

#endif /* QUANTUM2626_RATES_H */
