# Quantum 2626 Register Evidence

This table supersedes the earlier Windows-first guesses. Evidence recovered by decompiling a
vendor binary is labeled **static analysis** and is not a live Linux observation.

## TCI Mailbox — Static Analysis

| Offset | Direction | Meaning |
|---:|---|---|
| `0x0070` | read | TCI DMA status; stop waits for bits `0x10001` to clear |
| `0x0074` | read | TX device/consumer position |
| `0x0078` | read | RX device/producer position |
| `0x007c` | read | configuration: low byte slot count, upper 16 bits slot size |
| `0x0080 + 4*n` | read | RX message length for slot `n` |
| `0x1000` | write | TCI DMA control: `0x101` start, `0` stop |
| `0x1004` | read/write | TX host/producer position |
| `0x1008` | read/write | RX host/consumer position |
| `0x1010/0x1014 + 8*n` | write | TX slot DMA address low/high |
| `0x1090 + 4*n` | write | TX message length for slot `n` |
| `0x10d0/0x10d4 + 8*n` | write | RX slot DMA address low/high |

## Interrupts — Static Analysis

| Offset | Meaning |
|---:|---|
| `0x10004` | interrupt status and write-one-to-clear acknowledgement |
| `0x11004` | interrupt mask; vendor code uses an in-memory shadow and exact writes, not MMIO read-modify-write |
| bit `8` | audio DMA interrupt |
| bit `31` | TCI RX interrupt |

## Audio DMA — Static Analysis And Initial Linux Implementation

| Offset | Meaning |
|---:|---|
| `0x10000` | stop-status; stop waits for low two bits to clear |
| `0x10104` | packed DMA position: low 20 bits are frame offset within the buffer; high 12 bits are the wrapping buffer-cycle counter |
| `0x10200` | low byte capture channel count, next byte playback channel count |
| `0x10300` | record addresses per segment; read-only geometry |
| `0x10304` | playback addresses per segment; read-only geometry |
| `0x10308` | record/playback page-table fetch status |
| `0x11000` | main audio DMA control: `3` start, `0` stop |
| `0x11100/0x11104` | record page-table address low/high |
| `0x11108` | record DMA buffer length in frames |
| `0x1110c` | record hardware block length in frames; 128 at the current 48 kHz baseline |
| `0x11110/0x11114` | playback page-table address low/high |
| `0x11118` | playback DMA buffer length in frames |
| `0x1111c` | playback hardware block length in frames; 128 at the current 48 kHz baseline |

Page tables consist of 4 KiB coherent pages containing little-endian 64-bit entries. Data entries
are `DMA page address | 1`; when another table page follows, the next entry after the device-reported
data-entry count is `next table page address | 1`. The current Linux slice expresses this layout
directly. The second bounded silence run reached page status `0x00000101`, raised bit-8 interrupts,
and captured transient nonzero `0x10104` values such as `0x00400003` and `0x00a00001`.

**Observed Linux, 2026-08-15:** the local `1c67:0104` reports 15 record and 15 playback addresses per
segment. `0x10200 = 0x00001a1a`, confirming 26 channels in both directions.

## Legacy Identity Reads

Offsets `0x0000`, `0x0004`, `0x0008`, `0x0010`, `0x0014`, and `0x0104` are read during vendor
initialization. Their detailed bit fields remain unknown. Earlier claims that `0x0100` was the main
stream control and that `0x10300`/`0x10304` accepted ALSA buffer addresses are retired.

## Remaining Questions

- Whether the low 24 bits of each live-proven S32_LE container carry left-justified or
  right-justified 24-bit converter data; normal ALSA-generated S32_LE playback is audible.
- Physical confirmation of the statically recovered Line, S/PDIF, and ADAT output order. See
  `notes/CHANNEL_ROUTING.md` for the exact vendor tables and current Linux mapping.
- Whether the one-sided page-fetch timeout after 369 rapid xrun recovery cycles is fully explained
  by the now-corrected buffer-position accounting; the later bounded run no longer stormed.
- Whether any model- or firmware-specific TCI differences exist for `1c67:0104`.
