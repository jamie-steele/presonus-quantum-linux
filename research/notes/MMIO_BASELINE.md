# Quantum 2626 MMIO baseline (BAR 0)

First 64 bytes of BAR 0 as read by the driver at probe (Thunderbolt-attached Quantum 2626, card 4). Use for reverse-engineering register layout (compare with `pae_quantum.sys` or experimentation).

| Offset | Value      | Notes |
|--------|------------|--------|
| 0x00   | 0x00000000 | |
| 0x04   | 0x01030060 | Non-zero; possible ID/version or config |
| 0x08   | 0x00000010 | |
| 0x0c   | 0xffffffff | Likely unimplemented / read-as-one |
| 0x10   | 0x00000000 | |
| 0x14   | 0x00000000 | |
| 0x18–0x3c | 0xffffffff | Likely unimplemented |

Legacy PCI IRQ was 0 (invalid on x86); driver uses MSI when available, else timer fallback.
