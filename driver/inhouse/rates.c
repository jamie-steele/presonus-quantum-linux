// SPDX-License-Identifier: GPL-2.0-only

#include <linux/kernel.h>

#include "rates.h"

const struct quantum_rate_profile quantum_rate_profiles[QUANTUM_RATE_PROFILE_COUNT] = {
	{ 44100,  26, 1 },
	{ 48000,  26, 2 },
	{ 88200,  18, 3 },
	{ 96000,  18, 4 },
	{ 176400,  8, 5 },
	{ 192000,  8, 6 },
};

const struct quantum_rate_profile *
quantum_rate_profile_for_rate(unsigned int rate)
{
	unsigned int i;

	for (i = 0; i < ARRAY_SIZE(quantum_rate_profiles); i++)
		if (quantum_rate_profiles[i].rate == rate)
			return &quantum_rate_profiles[i];

	return NULL;
}

unsigned int quantum_tci_decode_sample_rate(u32 value)
{
	unsigned int i;

	for (i = 0; i < ARRAY_SIZE(quantum_rate_profiles); i++)
		if (quantum_rate_profiles[i].tci_value == value)
			return quantum_rate_profiles[i].rate;

	return 0;
}
