# TCI Protocol Notes

## Provenance

These facts are **static analysis**, recovered on 2026-08-15 from the x86_64 slice of version
2.19.0 of the vendor's macOS DriverKit extension, distributed inside the publicly downloadable
Universal Control 5.1.1.113315 installer. The source artifact and all decompiler output remain in
`/tmp` and must not be committed or redistributed.

- Installer SHA-256: `37734bd937d40ed5a4e19b9c3d916202641e144da812b3b629cadd9026e1fbf8`
- DriverKit binary SHA-256: `6233329562515f842449e63785ab1dc5608ed1d6d1e53919fd9e61add6403e89`
- x86_64 slice SHA-256: `ab862e84d7c2428852ee65e437113ff1b53d75ddc2deae4d7244aaebdbb20039`
- The extension's PCI match includes `0x01041c67`, corresponding to the Quantum 2626.

No vendor code has been copied into the Linux implementation. Register accesses and wire values
were independently expressed using Linux PCI/DMA APIs.

## Message Header

All multi-byte fields are little endian. Header length is eight bytes.

| Byte | Width | Field |
|---:|---:|---|
| `0` | 2 | total message length, including this header |
| `2` | 1 | channel |
| `3` | 1 | message code |
| `4` | 2 | transaction ID |
| `6` | 2 | reserved, written as zero |

Control requests and responses use channel `0x31`. Asynchronous control events use channel `0x32`.

## Cross-load response retention

Bounded Linux probes show that a control response can survive TCI stop, DMA-register cleanup, module
unload, and a later TCI start. In the current retained state, a 250 ms passive RX drain after start
reported an empty ring. The prior probe's power response (`0x3c`, transaction ID 33369) appeared only
after the next load submitted a new power request (transaction ID 0). Linux acknowledged and skipped
that stale response, but the new response did not arrive within its fresh 250 ms window.

This is observed cross-load behavior, not yet a complete mechanism. It establishes that passive ring
draining cannot clear that retained state and that the device accepted a nonzero transaction ID.
After a user-controlled full interface power cycle, the same Linux artifact completed power, clock,
and sample-rate queries without a stale header and registered its ALSA card. Immediate unload was
clean. The power cycle therefore cleared the retained condition, but the mechanism that allowed it
to survive software teardown remains unresolved.

## Minimum Control Commands

| Request | Response | Payload |
|---:|---:|---|
| `0x31` get sample rate | `0x35` | request: one clock-source `u32`; response: device-rate enum then clock-rate enum, each `u32` |
| `0x33` get clock source | `0x36` | response: one clock-source `u32` |
| `0x3b` get power state | `0x3c` | response: `u32`, restricted to `0` or `1` |

The statically recovered sample-rate setter uses request `0x32`. Its eight-byte payload is the
clock-source wire enum followed by the sample-rate wire enum, both little-endian `u32`. It expects
control response code `0x01` with one little-endian `u32` status; zero is success. The vendor path
stops DMA and frees its DMA resources before issuing the setter, then reads the rate back. This is
static-analysis evidence from the exact x86_64 DriverKit slice, not yet an observed Linux write.

Additional statically identified commands are `0x34` set clock source, `0x38` set serial number,
`0x39` get serial number, and `0x3d` get latency.

Sample-rate enum values are `1=44100`, `2=48000`, `3=88200`, `4=96000`, `5=176400`, and
`6=192000`; zero means no valid rate.

## Ring Ownership And Ordering

- The host writes TX data and length before advancing `0x1004`.
- The device advances `0x0074` after consuming TX slots.
- The device writes RX data and length before advancing `0x0078`.
- The host validates/copies an RX message before advancing `0x1008`.
- Producer/consumer positions wrap modulo the configured slot count and leave one slot empty to
  distinguish full from empty.
- Linux uses coherent DMA allocations plus `dma_wmb()` before publishing TX and `dma_rmb()` after
  observing an RX producer change.

## Current Linux Boundary

The driver starts TCI and performs the three queries above during probe, each with a 250 ms timeout.
The repository source now also implements the bounded `0x32` setter, status check, sample-rate
read-back, and rate-dependent channel-register check for ALSA `hw_params`; no installed or loaded
module has exercised that write. A successful compile is not hardware proof; live values belong in
`notes/CURRENT_STATUS.md` and the active task only after a bounded module load.
