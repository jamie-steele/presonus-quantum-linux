#!/usr/bin/env python3
"""Fail-closed Quantum 2626 analog loopback continuity soak.

The offline ``self-test`` command never connects to PipeWire.  The ``inspect``
command only reads the PipeWire registry.  The ``run`` command opens either the
exact Line Outputs 3-4 and Line Input 3 PipeWire nodes or the direct 26-channel
ALSA hardware PCM and therefore requires an explicit live-action acknowledgement.
"""

from __future__ import annotations

import argparse
import array
import collections
import datetime as dt
import fcntl
import json
import math
import os
import pathlib
import resource
import select
import shutil
import signal
import statistics
import struct
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from typing import Iterable, Sequence


RATE = 44_100
PERIOD_FRAMES = 128
BUFFER_FRAMES = 512
HARDWARE_CHANNELS = 26
REFERENCE_FRAMES = 8_191
ANALYSIS_FRAMES = 4_096
MAX_CONSECUTIVE_LOST_BLOCKS = 16
PLAYBACK_FRAGMENT = "quantum2626_stereo_out_P2626_0_2_3__sink"
CAPTURE_FRAGMENT = "quantum2626_mono_in_P2626_0_2__source"
ALSA_DEVICE = "hw:P2626,0"
DIRECT_CHANNEL_INDEX = 2
LIVE_ACK = "OUT3-PATCHED-TO-SELECTED-INPUT-MONITOR-OFF"
INT32_MAX = (1 << 31) - 1
PIPE_BYTES = 1 << 20
MAX_RECORDED_THREADS = 32
RTKIT_MAX_PRIORITY = 20
RTKIT_RTTIME_USEC = 200_000
RTKIT_SERVICE = "org.freedesktop.RealtimeKit1"
RTKIT_PATH = "/org/freedesktop/RealtimeKit1"
RTKIT_METHOD = "org.freedesktop.RealtimeKit1.MakeThreadRealtimeWithPID"
ALSA_HW_PARAM_PATHS = {
    "playback": pathlib.Path("/proc/asound/P2626/pcm0p/sub0/hw_params"),
    "capture": pathlib.Path("/proc/asound/P2626/pcm0c/sub0/hw_params"),
}


class SoakError(RuntimeError):
    """A fail-closed precondition or runtime invariant failed."""


def capture_extractor_geometry(transport: str) -> tuple[int, int]:
    """Return the raw capture geometry drained by the isolated extractor."""
    if transport == "pipewire":
        return (1, 0)
    if transport == "alsa":
        return (HARDWARE_CHANNELS, DIRECT_CHANNEL_INDEX)
    raise SoakError(f"unsupported transport: {transport}")


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds")


def json_line(handle, kind: str, **fields: object) -> None:
    record = {"time_utc": utc_now(), "monotonic_ns": time.monotonic_ns(), "kind": kind}
    record.update(fields)
    handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
    handle.flush()


def dbfs_to_linear(value: float) -> float:
    return 10.0 ** (value / 20.0)


def xorshift32(state: int) -> int:
    state ^= (state << 13) & 0xFFFFFFFF
    state ^= state >> 17
    state ^= (state << 5) & 0xFFFFFFFF
    return state & 0xFFFFFFFF


def make_reference(frames: int = REFERENCE_FRAMES) -> list[float]:
    """Return a deterministic, circular, lightly band-limited noise sequence."""
    raw: list[float] = []
    state = 0x26264410
    for _ in range(frames):
        state = xorshift32(state)
        raw.append(((state / 0xFFFFFFFF) * 2.0) - 1.0)

    taps = (1.0, 2.0, 3.0, 4.0, 3.0, 2.0, 1.0)
    tap_sum = sum(taps)
    filtered = []
    for index in range(frames):
        value = 0.0
        for offset, tap in enumerate(taps):
            value += raw[(index + offset - 3) % frames] * tap
        filtered.append(value / tap_sum)
    peak = max(abs(value) for value in filtered)
    return [value / peak for value in filtered]


def interleaved_playback_period(
    reference: Sequence[float], level_dbfs: float, channels: int, channel_index: int
) -> bytes:
    """Build interleaved S32_LE with the test sequence on exactly one channel."""
    if channels < 1 or not 0 <= channel_index < channels:
        raise SoakError(
            f"invalid interleaved playback geometry: channels={channels} channel={channel_index}"
        )
    amplitude = dbfs_to_linear(level_dbfs) * INT32_MAX
    samples = array.array("i")
    for value in reference:
        frame = [0] * channels
        frame[channel_index] = int(round(value * amplitude))
        samples.extend(frame)
    if sys.byteorder != "little":
        samples.byteswap()
    return samples.tobytes()


def playback_period(reference: Sequence[float], level_dbfs: float) -> bytes:
    """Build stereo S32_LE: test sequence on Line Out 3, silence on Line Out 4."""
    return interleaved_playback_period(reference, level_dbfs, 2, 0)


def extract_s32le_channel(payload: bytes, channels: int, channel_index: int) -> bytes:
    """Extract one S32_LE channel without changing its integer sample values."""
    frame_bytes = channels * 4
    if channels < 1 or not 0 <= channel_index < channels or len(payload) % frame_bytes:
        raise SoakError(
            "invalid interleaved capture payload: "
            f"bytes={len(payload)} channels={channels} channel={channel_index}"
        )
    samples = array.array("i")
    samples.frombytes(payload)
    if sys.byteorder != "little":
        samples.byteswap()
    selected = array.array("i", samples[channel_index::channels])
    if sys.byteorder != "little":
        selected.byteswap()
    return selected.tobytes()


def extract_channel_stream(
    source,
    destination,
    channels: int,
    channel_index: int,
    block_frames: int,
    ready_fd: int | None = None,
) -> None:
    """Continuously drain interleaved capture and forward one channel."""
    if ready_fd is not None:
        try:
            os.write(ready_fd, b"R")
        except OSError as error:
            raise SoakError(f"cannot signal capture extractor readiness: {error}") from error
        finally:
            os.close(ready_fd)
    block_bytes = block_frames * channels * 4
    while True:
        payload = source.read(block_bytes)
        if not payload:
            return
        while len(payload) < block_bytes:
            chunk = source.read(block_bytes - len(payload))
            if not chunk:
                raise SoakError(
                    f"short extractor block: {len(payload)} of {block_bytes} bytes"
                )
            payload += chunk
        destination.write(extract_s32le_channel(payload, channels, channel_index))
        destination.flush()


def decode_s32le(payload: bytes) -> list[float]:
    samples = array.array("i")
    samples.frombytes(payload)
    if sys.byteorder != "little":
        samples.byteswap()
    return [value / INT32_MAX for value in samples]


def signed_phase_delta(actual: int, expected: int, modulus: int) -> int:
    delta = (actual - expected) % modulus
    if delta > modulus // 2:
        delta -= modulus
    return delta


def correlation_at(
    samples: Sequence[float], reference: Sequence[float], phase: int, stride: int
) -> float:
    count = (len(samples) + stride - 1) // stride
    if count < 8:
        return 0.0
    sum_x = sum_y = sum_xx = sum_yy = sum_xy = 0.0
    modulus = len(reference)
    used = 0
    for index in range(0, len(samples), stride):
        x = reference[(phase + index) % modulus]
        y = samples[index]
        sum_x += x
        sum_y += y
        sum_xx += x * x
        sum_yy += y * y
        sum_xy += x * y
        used += 1
    covariance = sum_xy - (sum_x * sum_y / used)
    variance_x = sum_xx - (sum_x * sum_x / used)
    variance_y = sum_yy - (sum_y * sum_y / used)
    denominator = math.sqrt(max(variance_x * variance_y, 0.0))
    return covariance / denominator if denominator > 1e-20 else 0.0


def best_phase(
    samples: Sequence[float],
    reference: Sequence[float],
    candidates: Iterable[int],
    stride: int,
) -> tuple[int, float]:
    modulus = len(reference)
    best_candidate = 0
    best_correlation = 0.0
    for candidate in candidates:
        phase = candidate % modulus
        correlation = correlation_at(samples, reference, phase, stride)
        if abs(correlation) > abs(best_correlation):
            best_candidate = phase
            best_correlation = correlation
    return best_candidate, best_correlation


@dataclass
class Analysis:
    phase: int
    correlation: float
    phase_delta: int
    rms_dbfs: float
    peak_dbfs: float
    event: str | None
    lock_status: str
    loss_blocks: int
    global_search: bool


class PhaseTracker:
    def __init__(self, reference: Sequence[float]) -> None:
        self.reference = reference
        self.expected_phase: int | None = None
        self.correlations: collections.deque[float] = collections.deque(maxlen=100)
        self.loss_blocks = 0

    def global_phase(self, samples: Sequence[float]) -> tuple[int, float]:
        """Find sample-exact phase without assuming proximity to the prior block."""
        coarse, _ = best_phase(samples, self.reference, range(0, len(self.reference), 4), 16)
        return best_phase(samples, self.reference, range(coarse - 12, coarse + 13), 1)

    def acquire(self, samples: Sequence[float]) -> tuple[int, float]:
        # Coarse global acquisition followed by sample-exact refinement.
        fine, correlation = self.global_phase(samples)
        self.expected_phase = fine
        return fine, correlation

    def analyze(self, samples: Sequence[float]) -> Analysis:
        if not samples:
            raise SoakError("empty analysis block")
        peak = max(abs(value) for value in samples)
        rms = math.sqrt(sum(value * value for value in samples) / len(samples))
        peak_dbfs = 20.0 * math.log10(max(peak, 1e-15))
        rms_dbfs = 20.0 * math.log10(max(rms, 1e-15))

        if self.expected_phase is None:
            phase, correlation = self.acquire(samples)
            delta = 0
            event = None
            lock_status = "locked"
            loss_blocks = 0
            global_search = True
            self.correlations.append(abs(correlation))
            self.expected_phase = (phase + len(samples)) % len(self.reference)
        else:
            expected = self.expected_phase
            phase, correlation = best_phase(
                samples, self.reference, range(expected - 2, expected + 3), 4
            )
            baseline = statistics.median(self.correlations) if self.correlations else 0.0
            threshold = max(0.45, abs(baseline) * 0.70)
            global_search = abs(correlation) < threshold
            if global_search:
                phase, correlation = self.global_phase(samples)

            previously_lost = self.loss_blocks > 0
            if abs(correlation) < threshold:
                # A low-confidence phase must not move the expected timeline.
                # Count the episode once while continuing global recovery.
                phase = expected
                delta = 0
                self.loss_blocks += 1
                loss_blocks = self.loss_blocks
                lock_status = "lost"
                event = "correlation_drop" if loss_blocks == 1 else None
                self.expected_phase = (expected + len(samples)) % len(self.reference)
            else:
                delta = signed_phase_delta(phase, expected, len(self.reference))
                loss_blocks = self.loss_blocks
                self.loss_blocks = 0
                lock_status = "recovered" if previously_lost else "locked"
                if previously_lost:
                    # Recovery closes the existing loss episode. Its measured
                    # displacement is evidence, but not a second defect event.
                    event = None
                elif global_search and abs(delta) >= 3:
                    event = "phase_jump"
                else:
                    event = None
                self.correlations.append(abs(correlation))
                self.expected_phase = (phase + len(samples)) % len(self.reference)

        return Analysis(
            phase,
            correlation,
            delta,
            rms_dbfs,
            peak_dbfs,
            event,
            lock_status,
            loss_blocks,
            global_search,
        )


def synthetic_block(
    reference: Sequence[float], phase: int, frames: int, gain: float, noise: float, seed: int
) -> list[float]:
    output = []
    state = seed
    for index in range(frames):
        state = xorshift32(state)
        perturbation = (((state / 0xFFFFFFFF) * 2.0) - 1.0) * noise
        output.append(reference[(phase + index) % len(reference)] * gain + 0.012 + perturbation)
    return output


def run_self_test() -> None:
    reference = make_reference()
    packed = playback_period(reference, -30.0)
    if len(packed) != len(reference) * 2 * 4:
        raise SoakError("stereo S32_LE fixture has the wrong byte count")
    unpacked = struct.iter_unpack("<ii", packed)
    left_peak = 0
    for left, right in unpacked:
        if right != 0:
            raise SoakError("Line Out 4 guard channel is not silent")
        left_peak = max(left_peak, abs(left))
    expected_peak = int(round(dbfs_to_linear(-30.0) * INT32_MAX))
    if abs(left_peak - expected_peak) > 1:
        raise SoakError(f"playback level mismatch: {left_peak} versus {expected_peak}")
    direct_packed = interleaved_playback_period(
        reference, -30.0, HARDWARE_CHANNELS, DIRECT_CHANNEL_INDEX
    )
    if len(direct_packed) != len(reference) * HARDWARE_CHANNELS * 4:
        raise SoakError("direct-ALSA S32_LE fixture has the wrong byte count")
    direct_selected = extract_s32le_channel(
        direct_packed, HARDWARE_CHANNELS, DIRECT_CHANNEL_INDEX
    )
    direct_values = array.array("i")
    direct_values.frombytes(direct_selected)
    stereo_values = array.array("i")
    stereo_values.frombytes(packed)
    if sys.byteorder != "little":
        direct_values.byteswap()
        stereo_values.byteswap()
    if list(direct_values) != list(stereo_values[0::2]):
        raise SoakError("direct-ALSA channel extraction changed playback samples")
    direct_all = array.array("i")
    direct_all.frombytes(direct_packed)
    if sys.byteorder != "little":
        direct_all.byteswap()
    for channel in range(HARDWARE_CHANNELS):
        if channel == DIRECT_CHANNEL_INDEX:
            continue
        if any(direct_all[channel::HARDWARE_CHANNELS]):
            raise SoakError(f"direct-ALSA guard channel {channel} is not silent")
    ready_read, ready_write = os.pipe()
    extractor = subprocess.Popen(
        [
            sys.executable,
            str(pathlib.Path(__file__).resolve()),
            "extract-channel",
            "--channels",
            str(HARDWARE_CHANNELS),
            "--channel-index",
            str(DIRECT_CHANNEL_INDEX),
            "--block-frames",
            str(len(reference)),
            "--ready-fd",
            str(ready_write),
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        pass_fds=(ready_write,),
    )
    os.close(ready_write)
    try:
        wait_for_extractor_ready(extractor, ready_read)
    finally:
        os.close(ready_read)
    extractor_stdout, extractor_stderr = extractor.communicate(input=direct_packed * 3)
    if extractor.returncode != 0:
        raise SoakError(
            "isolated capture extractor failed: "
            + extractor_stderr.decode("utf-8", errors="replace").strip()
        )
    if extractor_stdout != direct_selected * 3:
        raise SoakError("isolated capture extractor changed selected samples")
    if capture_extractor_geometry("pipewire") != (1, 0):
        raise SoakError("PipeWire capture extractor lost mono passthrough geometry")
    if capture_extractor_geometry("alsa") != (HARDWARE_CHANNELS, DIRECT_CHANNEL_INDEX):
        raise SoakError("direct-ALSA capture extractor lost hardware geometry")

    pipewire_ready_read, pipewire_ready_write = os.pipe()
    pipewire_extractor = subprocess.Popen(
        [
            sys.executable,
            str(pathlib.Path(__file__).resolve()),
            "extract-channel",
            "--channels",
            "1",
            "--channel-index",
            "0",
            "--block-frames",
            str(len(reference)),
            "--ready-fd",
            str(pipewire_ready_write),
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        pass_fds=(pipewire_ready_write,),
    )
    os.close(pipewire_ready_write)
    try:
        wait_for_extractor_ready(pipewire_extractor, pipewire_ready_read)
    finally:
        os.close(pipewire_ready_read)
    if pipewire_extractor.stdin is None or pipewire_extractor.stdout is None:
        raise SoakError("PipeWire extractor fixture has incomplete pipes")
    pipewire_raw_pipe = set_pipe_capacity(pipewire_extractor.stdin)
    pipewire_mono_pipe = set_pipe_capacity(pipewire_extractor.stdout)
    mono_fixture = direct_selected * 3
    pipewire_stdout, pipewire_stderr = pipewire_extractor.communicate(input=mono_fixture)
    if pipewire_extractor.returncode != 0:
        raise SoakError(
            "PipeWire isolated capture extractor failed: "
            + pipewire_stderr.decode("utf-8", errors="replace").strip()
        )
    if pipewire_stdout != mono_fixture:
        raise SoakError("PipeWire isolated capture extractor changed mono samples")
    pipewire_buffer_seconds = min(pipewire_raw_pipe, pipewire_mono_pipe) / (RATE * 4)
    maximum_loss_seconds = MAX_CONSECUTIVE_LOST_BLOCKS * ANALYSIS_FRAMES / RATE
    if pipewire_buffer_seconds <= maximum_loss_seconds:
        raise SoakError(
            "PipeWire capture isolation cannot absorb the fail-closed analysis window: "
            f"buffer={pipewire_buffer_seconds:.6f}s required>{maximum_loss_seconds:.6f}s"
        )
    pipe_read, pipe_write = os.pipe()
    try:
        resized_pipe = set_pipe_capacity(pipe_write)
    finally:
        os.close(pipe_read)
        os.close(pipe_write)
    if resized_pipe < PIPE_BYTES:
        raise SoakError(f"transport pipe remained too small: {resized_pipe}")
    scheduling = process_scheduling(os.getpid())
    required_scheduling = {
        "policy",
        "priority",
        "nice",
        "voluntary_context_switches",
        "nonvoluntary_context_switches",
        "runtime_ns",
        "wait_ns",
        "timeslices",
    }
    if scheduling.get("state") != "running" or not required_scheduling.issubset(scheduling):
        raise SoakError(f"process scheduling fixture incomplete: {scheduling}")
    thread_scheduling = process_threads_scheduling(os.getpid())
    if (
        thread_scheduling.get("state") != "running"
        or not thread_scheduling.get("threads")
        or not any(
            thread.get("tid") == os.getpid()
            for thread in thread_scheduling.get("threads", [])
        )
    ):
        raise SoakError(f"thread scheduling fixture incomplete: {thread_scheduling}")
    validate_process_threads_scheduling({"self_test": thread_scheduling})
    if not is_pipewire_data_loop("pipewire", "data-loop.0"):
        raise SoakError("PipeWire data-loop matcher rejected a valid server thread")
    if not is_pipewire_data_loop("pipewire", "pw-data-loop"):
        raise SoakError("PipeWire data-loop matcher rejected the host server thread")
    if is_pipewire_data_loop("pw-play", "data-loop.0"):
        raise SoakError("PipeWire data-loop matcher admitted a client helper thread")
    if is_pipewire_data_loop("pw-play", "pw-data-loop"):
        raise SoakError("PipeWire data-loop matcher admitted a host-named client thread")
    if is_pipewire_data_loop("pipewire", "pw-data-looper"):
        raise SoakError("PipeWire data-loop matcher admitted a lookalike thread")
    terminal_child = subprocess.Popen([sys.executable, "-c", "pass"])
    try:
        deadline = time.monotonic() + 2.0
        exit_observation = child_exit_status(terminal_child.pid)
        while exit_observation is None and time.monotonic() < deadline:
            time.sleep(0.001)
            exit_observation = child_exit_status(terminal_child.pid)
        if exit_observation is None or exit_observation.get("state") != "exited_unreaped":
            raise SoakError(
                f"non-reaping child-exit fixture did not observe exit: {exit_observation}"
            )
        terminal_scheduling = process_scheduling(terminal_child.pid)
        if terminal_scheduling.get("process_state", "").split(maxsplit=1)[0] != "Z":
            raise SoakError(
                "terminal scheduling fixture did not preserve the exited child: "
                f"{terminal_scheduling}"
            )
        snapshot = terminal_evidence(
            "offline fixture",
            time.monotonic(),
            "pipewire",
            {},
            terminal_child,
            None,
            None,
            None,
            None,
        )
        snapshot_exit = snapshot["child_exit_observations"]["playback_helper"]
        if snapshot_exit is None or snapshot_exit.get("state") != "exited_unreaped":
            raise SoakError(f"terminal evidence fixture lost child exit: {snapshot}")
    finally:
        terminal_child.wait()
    rtkit_fixture = subprocess.Popen(
        [
            sys.executable,
            "-c",
            (
                "import resource,time; "
                "print(resource.getrlimit(resource.RLIMIT_RTTIME), flush=True); "
                "time.sleep(2)"
            ),
        ],
        stdout=subprocess.PIPE,
        text=True,
        preexec_fn=prepare_rtkit_target,
    )
    try:
        if rtkit_fixture.stdout is None:
            raise SoakError("RTKit prerequisite fixture has no stdout")
        observed_limit = rtkit_fixture.stdout.readline().strip()
        rtkit_scheduling = process_scheduling(rtkit_fixture.pid)
        if observed_limit != f"({RTKIT_RTTIME_USEC}, {RTKIT_RTTIME_USEC})":
            raise SoakError(f"RTKit RTTIME fixture mismatch: {observed_limit!r}")
        if not rtkit_scheduling.get("reset_on_fork"):
            raise SoakError(
                f"RTKit reset-on-fork fixture mismatch: {rtkit_scheduling}"
            )
    finally:
        if rtkit_fixture.poll() is None:
            rtkit_fixture.terminate()
            rtkit_fixture.wait(timeout=2)
    expected_rtkit_command = [
        "gdbus",
        "call",
        "--system",
        "--dest",
        RTKIT_SERVICE,
        "--object-path",
        RTKIT_PATH,
        "--method",
        RTKIT_METHOD,
        "1234",
        "1234",
        str(RTKIT_MAX_PRIORITY),
    ]
    if rtkit_command(1234, RTKIT_MAX_PRIORITY) != expected_rtkit_command:
        raise SoakError("RTKit command fixture changed the bounded method call")
    validate_rtkit_scheduling(
        {
            "playback_helper": {
                "state": "running",
                "policy": "SCHED_RR",
                "priority": RTKIT_MAX_PRIORITY,
                "reset_on_fork": True,
            },
            "capture_helper": {
                "state": "running",
                "policy": "SCHED_RR",
                "priority": RTKIT_MAX_PRIORITY,
                "reset_on_fork": True,
            },
        },
        RTKIT_MAX_PRIORITY,
    )
    tracker = PhaseTracker(reference)
    source_phase = 1_337
    results: list[Analysis] = []

    for index in range(14):
        block = synthetic_block(reference, source_phase, ANALYSIS_FRAMES, 0.34, 0.002, index + 1)
        result = tracker.analyze(block)
        results.append(result)
        source_phase = (source_phase + ANALYSIS_FRAMES) % len(reference)

    # Simulate one repeated hardware period, then a skipped hardware period.
    source_phase = (source_phase - PERIOD_FRAMES) % len(reference)
    repeat = tracker.analyze(
        synthetic_block(reference, source_phase, ANALYSIS_FRAMES, 0.34, 0.002, 101)
    )
    source_phase = (source_phase + ANALYSIS_FRAMES + PERIOD_FRAMES) % len(reference)
    skip = tracker.analyze(
        synthetic_block(reference, source_phase, ANALYSIS_FRAMES, 0.34, 0.002, 102)
    )

    corruption_tracker = PhaseTracker(reference)
    corruption_phase = 733
    corruption_tracker.analyze(
        synthetic_block(reference, corruption_phase, ANALYSIS_FRAMES, 0.34, 0.002, 201)
    )
    corruption_phase = (corruption_phase + ANALYSIS_FRAMES) % len(reference)
    state = 0xBAD0C0DE
    corrupted = []
    for _ in range(ANALYSIS_FRAMES):
        state = xorshift32(state)
        corrupted.append((((state / 0xFFFFFFFF) * 2.0) - 1.0) * 0.12 + 0.012)
    corruption = corruption_tracker.analyze(corrupted)

    # A displacement beyond the old +/-320-frame window must globally
    # reacquire once, then remain locked without duplicate events.
    beyond_window_tracker = PhaseTracker(reference)
    beyond_window_phase = 2_041
    beyond_window_tracker.analyze(
        synthetic_block(reference, beyond_window_phase, ANALYSIS_FRAMES, 0.34, 0.002, 301)
    )
    beyond_window_phase = (
        beyond_window_phase + ANALYSIS_FRAMES + (PERIOD_FRAMES * 8)
    ) % len(reference)
    beyond_window = beyond_window_tracker.analyze(
        synthetic_block(reference, beyond_window_phase, ANALYSIS_FRAMES, 0.34, 0.002, 302)
    )
    beyond_window_phase = (beyond_window_phase + ANALYSIS_FRAMES) % len(reference)
    beyond_window_followup = beyond_window_tracker.analyze(
        synthetic_block(reference, beyond_window_phase, ANALYSIS_FRAMES, 0.34, 0.002, 303)
    )

    # Persistent corrupt content is one loss episode. Recovery advances from
    # the preserved expected timeline and is not counted as another event.
    recovery_tracker = PhaseTracker(reference)
    recovery_phase = 4_321
    recovery_tracker.analyze(
        synthetic_block(reference, recovery_phase, ANALYSIS_FRAMES, 0.34, 0.002, 401)
    )
    recovery_phase = (recovery_phase + ANALYSIS_FRAMES) % len(reference)
    loss_results = []
    for seed in range(402, 407):
        state = 0xBAD00000 + seed
        lost = []
        for _ in range(ANALYSIS_FRAMES):
            state = xorshift32(state)
            lost.append((((state / 0xFFFFFFFF) * 2.0) - 1.0) * 0.12 + 0.012)
        loss_results.append(recovery_tracker.analyze(lost))
        recovery_phase = (recovery_phase + ANALYSIS_FRAMES) % len(reference)
    recovery = recovery_tracker.analyze(
        synthetic_block(reference, recovery_phase, ANALYSIS_FRAMES, 0.34, 0.002, 407)
    )
    recovery_phase = (recovery_phase + ANALYSIS_FRAMES) % len(reference)
    recovery_followup = recovery_tracker.analyze(
        synthetic_block(reference, recovery_phase, ANALYSIS_FRAMES, 0.34, 0.002, 408)
    )

    if any(item.event for item in results[1:]):
        raise SoakError("clean/noisy fixture produced a false discontinuity")
    if repeat.event != "phase_jump" or repeat.phase_delta != -PERIOD_FRAMES:
        raise SoakError(
            f"repeated-period fixture mismatch: event={repeat.event} delta={repeat.phase_delta}"
        )
    if skip.event != "phase_jump" or skip.phase_delta != PERIOD_FRAMES:
        raise SoakError(f"skipped-period fixture mismatch: event={skip.event} delta={skip.phase_delta}")
    if corruption.event != "correlation_drop":
        raise SoakError(
            f"corrupted-content fixture mismatch: event={corruption.event} "
            f"correlation={corruption.correlation:.6f}"
        )
    if (
        beyond_window.event != "phase_jump"
        or beyond_window.phase_delta != PERIOD_FRAMES * 8
        or not beyond_window.global_search
    ):
        raise SoakError(
            "beyond-window fixture mismatch: "
            f"event={beyond_window.event} delta={beyond_window.phase_delta} "
            f"global={beyond_window.global_search}"
        )
    if beyond_window_followup.event is not None or beyond_window_followup.lock_status != "locked":
        raise SoakError("beyond-window fixture did not remain locked after global reacquisition")
    if [item.event for item in loss_results] != ["correlation_drop", None, None, None, None]:
        raise SoakError("persistent-loss fixture inflated one episode into multiple events")
    if [item.loss_blocks for item in loss_results] != [1, 2, 3, 4, 5]:
        raise SoakError("persistent-loss fixture did not retain its episode length")
    if recovery.event is not None or recovery.lock_status != "recovered":
        raise SoakError(
            f"recovery fixture mismatch: event={recovery.event} status={recovery.lock_status}"
        )
    if recovery.phase_delta != 0 or recovery.loss_blocks != len(loss_results):
        raise SoakError(
            f"recovery fixture phase mismatch: delta={recovery.phase_delta} "
            f"loss_blocks={recovery.loss_blocks}"
        )
    if recovery_followup.event is not None or recovery_followup.lock_status != "locked":
        raise SoakError("recovery fixture did not remain locked")

    fixture_nodes = {"playback": {"name": "fixture-sink"}, "capture": {"name": "fixture-source"}}
    pipewire_commands = stream_commands("pipewire", fixture_nodes)
    alsa_commands = stream_commands("alsa", fixture_nodes)
    if pipewire_commands[0][0] != "pw-play" or pipewire_commands[1][0] != "pw-record":
        raise SoakError("PipeWire command fixture selected the wrong helpers")
    if alsa_commands[0][0] != "aplay" or alsa_commands[1][0] != "arecord":
        raise SoakError("direct-ALSA command fixture selected the wrong helpers")
    for command in alsa_commands:
        required = {
            ALSA_DEVICE,
            str(RATE),
            str(HARDWARE_CHANNELS),
            str(PERIOD_FRAMES),
            str(BUFFER_FRAMES),
            "S32_LE",
        }
        if (
            not required.issubset(command)
            or "--mmap" not in command
            or "--fatal-errors" not in command
        ):
            raise SoakError(f"direct-ALSA command fixture lost exact geometry: {command}")

    parsed_sink = parse_pw_top_row(
        "R 186 256 44100 16.2us 86.0us 0.00 0.01 33 S32P 2 44100 fixture-sink",
        fixture_nodes,
    )
    parsed_playback = parse_pw_top_row(
        "R 45 256 44100 6.3us 6.8us 0.00 0.00 1 S32LE 2 44100 + pw-play",
        fixture_nodes,
    )
    if (
        parsed_sink is None
        or parsed_sink.get("role") != "playback_node"
        or parsed_sink.get("errors") != 33
        or parsed_playback is None
        or parsed_playback.get("role") != "playback_helper"
    ):
        raise SoakError(
            f"pw-top parser fixture mismatch: sink={parsed_sink} playback={parsed_playback}"
        )
    error_tracker = PipeWireErrorTracker()
    first_transition = error_tracker.update(parsed_playback)
    unchanged_transition = error_tracker.update(parsed_playback)
    changed_playback = dict(parsed_playback)
    changed_playback["errors"] = 4
    changed_transition = error_tracker.update(changed_playback)
    if (
        first_transition is None
        or first_transition.get("previous_errors") is not None
        or unchanged_transition is not None
        or changed_transition is None
        or changed_transition.get("previous_errors") != 1
        or changed_transition.get("error_delta") != 3
    ):
        raise SoakError("PipeWire error-transition fixture lost initial/change semantics")

    # Verify that playback can run outside the analysis interpreter.
    read_fd, write_fd = os.pipe()
    feeder_payload = b"quantum2626-feeder-fixture"
    feeder_pid = spawn_playback_feeder(os.fdopen(write_fd, "wb", buffering=0), feeder_payload)
    received = bytearray()
    try:
        while len(received) < len(feeder_payload) * 3:
            chunk = os.read(read_fd, len(feeder_payload) * 3 - len(received))
            if not chunk:
                raise SoakError("isolated playback feeder ended before the fixture completed")
            received.extend(chunk)
    finally:
        os.close(read_fd)
        terminate_playback_feeder(feeder_pid)
    if received != feeder_payload * 3:
        raise SoakError("isolated playback feeder fixture mismatch")
    minimum = min(abs(item.correlation) for item in results)
    print(
        json.dumps(
            {
                "result": "pass",
                "clean_min_abs_correlation": round(minimum, 6),
                "repeated_period_delta_frames": repeat.phase_delta,
                "skipped_period_delta_frames": skip.phase_delta,
                "corrupted_content_event": corruption.event,
                "beyond_window_delta_frames": beyond_window.phase_delta,
                "persistent_loss_events": sum(item.event is not None for item in loss_results),
                "recovered_after_blocks": recovery.loss_blocks,
                "isolated_playback_feeder": True,
                "direct_alsa_channel": DIRECT_CHANNEL_INDEX,
                "direct_alsa_commands": True,
                "isolated_capture_extractor": True,
                "isolated_pipewire_capture": True,
                "capture_extractor_ready_handshake": True,
                "direct_alsa_pipe_bytes": resized_pipe,
                "pipewire_capture_pipe_bytes": min(
                    pipewire_raw_pipe, pipewire_mono_pipe
                ),
                "pipewire_capture_buffer_seconds": round(
                    pipewire_buffer_seconds, 6
                ),
                "pipewire_error_transition_telemetry": True,
                "process_scheduling_telemetry": True,
                "thread_scheduling_telemetry": True,
                "pipewire_data_loop_telemetry": True,
                "terminal_snapshot_before_reap": True,
                "rtkit_helper_ab_prepared": True,
                "analysis_frames": ANALYSIS_FRAMES,
                "reference_frames": REFERENCE_FRAMES,
            },
            sort_keys=True,
        )
    )


def replay_artifacts(artifact_dir: pathlib.Path) -> dict[str, object]:
    """Globally classify retained event blocks without changing their directory."""
    artifact_dir = artifact_dir.expanduser().resolve()
    log_path = artifact_dir / "events.jsonl"
    try:
        records = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    except (OSError, json.JSONDecodeError) as error:
        raise SoakError(f"cannot read replay log {log_path}: {error}") from error
    events = [record for record in records if record.get("kind") == "continuity_event"]
    if not events:
        raise SoakError("replay log contains no continuity events")

    reference = make_reference()
    tracker = PhaseTracker(reference)
    correlations = []
    original_events: collections.Counter[str] = collections.Counter()
    replayed_events = []
    seen_files = set()
    for expected_sequence, record in enumerate(events, start=1):
        if record.get("sequence") != expected_sequence:
            raise SoakError(
                f"replay event sequence mismatch at {expected_sequence}: {record.get('sequence')!r}"
            )
        name = record.get("capture_file")
        if not isinstance(name, str) or pathlib.Path(name).name != name or name in seen_files:
            raise SoakError(f"unsafe or duplicate replay capture name: {name!r}")
        seen_files.add(name)
        try:
            payload = (artifact_dir / name).read_bytes()
        except OSError as error:
            raise SoakError(f"cannot read replay capture {name}: {error}") from error
        if len(payload) != ANALYSIS_FRAMES * 4:
            raise SoakError(
                f"replay capture {name} has {len(payload)} bytes; expected {ANALYSIS_FRAMES * 4}"
            )
        _, correlation = tracker.global_phase(decode_s32le(payload))
        absolute = abs(correlation)
        correlations.append(absolute)
        original = str(record.get("event"))
        original_events[original] += 1
        replayed_events.append((original, absolute))

    threshold = max(0.45, statistics.median(correlations) * 0.70)
    classifications: collections.Counter[str] = collections.Counter()
    for original, absolute in replayed_events:
        if absolute >= threshold:
            classification = (
                "globally_reacquired" if original == "correlation_drop" else "globally_locked"
            )
        else:
            classification = "global_correlation_drop"
        classifications[classification] += 1

    return {
        "result": "pass",
        "mode": "read_only_event_replay",
        "artifact_dir": str(artifact_dir),
        "events_logged": len(events),
        "captures_replayed": len(correlations),
        "original_events": dict(sorted(original_events.items())),
        "classifications": dict(sorted(classifications.items())),
        "global_min_abs_correlation": round(min(correlations), 8),
        "global_median_abs_correlation": round(statistics.median(correlations), 8),
        "global_lock_threshold": round(threshold, 8),
    }


def pipewire_objects() -> list[dict]:
    try:
        completed = subprocess.run(
            ["pw-dump"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
    except (OSError, subprocess.CalledProcessError) as error:
        detail = getattr(error, "stderr", "") or str(error)
        raise SoakError(f"cannot read PipeWire registry: {detail.strip()}") from error
    try:
        value = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise SoakError(f"invalid pw-dump JSON: {error}") from error
    if not isinstance(value, list):
        raise SoakError("pw-dump root is not an object list")
    return value


def exact_node(fragment: str, media_class: str, objects: Sequence[dict]) -> dict:
    matches = []
    for item in objects:
        props = item.get("info", {}).get("props", {})
        name = str(props.get("node.name", ""))
        if fragment in name and props.get("media.class") == media_class:
            matches.append(
                {
                    "id": item.get("id"),
                    "name": name,
                    "description": props.get("node.description"),
                    "serial": props.get("object.serial"),
                    "media_class": props.get("media.class"),
                }
            )
    if len(matches) != 1:
        raise SoakError(
            f"expected exactly one {media_class} containing {fragment!r}; found {len(matches)}"
        )
    return matches[0]


def inspect_nodes(capture_fragment: str = CAPTURE_FRAGMENT) -> dict:
    objects = pipewire_objects()
    playback = exact_node(PLAYBACK_FRAGMENT, "Audio/Sink", objects)
    capture = exact_node(capture_fragment, "Audio/Source", objects)
    return {"playback": playback, "capture": capture}


def parse_hw_params(path: pathlib.Path) -> dict[str, str]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        raise SoakError(f"cannot read {path}: {error}") from error
    values: dict[str, str] = {}
    for line in text.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            values[key.strip()] = value.strip()
    if text.strip() == "closed":
        values["state"] = "closed"
    return values


def validate_geometry() -> dict[str, dict[str, str]]:
    expected = {
        "format": "S32_LE",
        "channels": str(HARDWARE_CHANNELS),
        "rate": str(RATE),
        "period_size": str(PERIOD_FRAMES),
        "buffer_size": str(BUFFER_FRAMES),
    }
    observed = {
        direction: parse_hw_params(path)
        for direction, path in ALSA_HW_PARAM_PATHS.items()
    }
    failures = []
    for direction, values in observed.items():
        for key, required in expected.items():
            actual = values.get(key)
            # ALSA reports rate as "44100 (44100/1)" on some kernels.
            if key == "rate" and actual and actual.split()[0] == required:
                continue
            if actual != required:
                failures.append(f"{direction}.{key}={actual!r}, required {required!r}")
    if failures:
        raise SoakError("unexpected ALSA geometry: " + "; ".join(failures))
    return observed


def irq_count() -> int | None:
    try:
        lines = pathlib.Path("/proc/interrupts").read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    for line in lines:
        if "snd_quantum2626" in line or "snd-quantum2626" in line:
            fields = line.split()
            total = 0
            for field in fields[1:]:
                if field.isdigit():
                    total += int(field)
                else:
                    break
            return total
    return None


def alsa_status(direction: str) -> dict[str, str] | None:
    suffix = "p" if direction == "playback" else "c"
    path = pathlib.Path(f"/proc/asound/P2626/pcm0{suffix}/sub0/status")
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    values = {}
    for line in text.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            values[key.strip()] = value.strip()
    return values


def wait_for_geometry(playback: subprocess.Popen, capture: subprocess.Popen) -> dict:
    deadline = time.monotonic() + 4.0
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        exits = {
            "playback_helper": child_exit_status(playback.pid),
            "capture_helper": child_exit_status(capture.pid),
        }
        if any(observation is not None for observation in exits.values()):
            raise SoakError(
                "audio stream exited before ALSA geometry validation without reap: "
                + json.dumps(exits, sort_keys=True)
            )
        try:
            return validate_geometry()
        except SoakError as error:
            last_error = error
        time.sleep(0.1)
    raise SoakError(f"ALSA geometry did not become exact within four seconds: {last_error}")


def wait_for_extractor_ready(
    process: subprocess.Popen, descriptor: int, timeout_seconds: float = 2.0
) -> None:
    """Wait until the isolated extractor is actively ready to drain capture."""
    readable, _, _ = select.select([descriptor], [], [], timeout_seconds)
    if not readable:
        raise SoakError("capture extractor did not become ready within two seconds")
    marker = os.read(descriptor, 1)
    if marker != b"R":
        raise SoakError(
            "capture extractor exited before readiness: "
            f"status={child_exit_status(process.pid)} marker={marker!r}"
        )


def set_pipe_capacity(handle_or_fd, requested: int = PIPE_BYTES) -> int:
    """Enlarge a transport pipe or fail before a live stream can depend on it."""
    descriptor = (
        handle_or_fd if isinstance(handle_or_fd, int) else handle_or_fd.fileno()
    )
    try:
        fcntl.fcntl(descriptor, fcntl.F_SETPIPE_SZ, requested)
        actual = fcntl.fcntl(descriptor, fcntl.F_GETPIPE_SZ)
    except OSError as error:
        raise SoakError(f"cannot size transport pipe to {requested} bytes: {error}") from error
    if actual < requested:
        raise SoakError(f"transport pipe is {actual} bytes, required {requested}")
    return actual


def child_exit_status(pid: int) -> dict[str, object] | None:
    """Observe a child exit without reaping it or destroying its /proc evidence."""
    try:
        information = os.waitid(
            os.P_PID,
            pid,
            os.WEXITED | os.WNOHANG | os.WNOWAIT,
        )
    except ChildProcessError:
        return {"pid": pid, "state": "not_child_or_reaped"}
    except OSError as error:
        return {"pid": pid, "state": "unavailable", "error": str(error)}
    if information is None:
        return None
    return {
        "pid": information.si_pid,
        "state": "exited_unreaped",
        "signal": information.si_signo,
        "code": information.si_code,
        "status": information.si_status,
    }


def process_scheduling(pid: int) -> dict[str, object]:
    """Return bounded scheduler and wait-accounting telemetry for one process or thread."""
    try:
        status_text = pathlib.Path(f"/proc/{pid}/status").read_text(encoding="utf-8")
        schedstat = pathlib.Path(f"/proc/{pid}/schedstat").read_text(encoding="utf-8").split()
    except (OSError, ProcessLookupError) as error:
        return {"pid": pid, "state": "unavailable", "error": str(error)}
    reset_flag = getattr(os, "SCHED_RESET_ON_FORK", 0)
    policy_names = {
        os.SCHED_OTHER: "SCHED_OTHER",
        os.SCHED_FIFO: "SCHED_FIFO",
        os.SCHED_RR: "SCHED_RR",
    }
    for optional_name in ("SCHED_BATCH", "SCHED_IDLE"):
        optional_value = getattr(os, optional_name, None)
        if optional_value is not None:
            policy_names[optional_value] = optional_name
    status = {}
    for line in status_text.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            status[key.strip()] = value.strip()
    if len(schedstat) != 3:
        return {"pid": pid, "state": "unavailable", "error": "invalid schedstat"}
    process_state = status.get("State", "unknown")
    result: dict[str, object] = {
        "pid": pid,
        "state": "exited_unreaped" if process_state.startswith("Z") else "running",
        "process_state": process_state,
        "voluntary_context_switches": int(status.get("voluntary_ctxt_switches", "0")),
        "nonvoluntary_context_switches": int(
            status.get("nonvoluntary_ctxt_switches", "0")
        ),
        "runtime_ns": int(schedstat[0]),
        "wait_ns": int(schedstat[1]),
        "timeslices": int(schedstat[2]),
    }
    try:
        policy = os.sched_getscheduler(pid)
        result.update(
            {
                "policy": policy_names.get(policy & ~reset_flag, str(policy)),
                "reset_on_fork": bool(policy & reset_flag),
                "priority": os.sched_getparam(pid).sched_priority,
                "nice": os.getpriority(os.PRIO_PROCESS, pid),
            }
        )
    except (OSError, ProcessLookupError) as error:
        result["scheduler_error"] = str(error)
    return result


def process_threads_scheduling(pid: int) -> dict[str, object]:
    """Return bounded scheduling telemetry for every thread owned by one helper."""
    task_root = pathlib.Path(f"/proc/{pid}/task")
    try:
        task_paths = sorted(
            (path for path in task_root.iterdir() if path.name.isdigit()),
            key=lambda path: int(path.name),
        )
    except OSError as error:
        return {"pid": pid, "state": "unavailable", "error": str(error)}
    selected = task_paths[:MAX_RECORDED_THREADS]
    threads = []
    for path in selected:
        tid = int(path.name)
        try:
            name = (path / "comm").read_text(encoding="utf-8").strip()
        except OSError:
            name = "unavailable"
        telemetry = process_scheduling(tid)
        telemetry.update({"tid": tid, "thread_name": name})
        threads.append(telemetry)
    return {
        "pid": pid,
        "state": "running",
        "threads": threads,
        "omitted_threads": max(0, len(task_paths) - len(selected)),
    }


def validate_process_threads_scheduling(
    scheduling: dict[str, dict[str, object]]
) -> None:
    """Fail unless every helper thread remains present and fully measurable."""
    required_fields = {"policy", "priority", "nice", "runtime_ns", "wait_ns", "timeslices"}
    failures = []
    for name, group in scheduling.items():
        threads = group.get("threads")
        if (
            group.get("state") != "running"
            or not isinstance(threads, list)
            or not threads
            or group.get("omitted_threads") != 0
        ):
            failures.append({"name": name, "group": group})
            continue
        unavailable = [
            thread
            for thread in threads
            if thread.get("state") != "running"
            or not required_fields.issubset(thread)
        ]
        if unavailable:
            failures.append({"name": name, "threads": unavailable})
    if failures:
        raise SoakError(
            "helper thread scheduling became unavailable: "
            + json.dumps(failures, sort_keys=True)
        )


def is_pipewire_data_loop(process_name: str, thread_name: str) -> bool:
    """Identify only server-owned PipeWire data-loop threads."""
    return process_name == "pipewire" and (
        thread_name == "pw-data-loop" or thread_name.startswith("data-loop")
    )


def discover_pipewire_data_loops() -> list[dict[str, object]]:
    """Discover this user's server data loops once, before live stream startup."""
    loops: list[dict[str, object]] = []
    try:
        process_paths = sorted(
            (path for path in pathlib.Path("/proc").iterdir() if path.name.isdigit()),
            key=lambda path: int(path.name),
        )
    except OSError:
        return loops
    for process_path in process_paths:
        try:
            process_name = (process_path / "comm").read_text(encoding="utf-8").strip()
            status = (process_path / "status").read_text(encoding="utf-8")
        except OSError:
            continue
        uid_line = next((line for line in status.splitlines() if line.startswith("Uid:")), "")
        uid_fields = uid_line.split()
        try:
            process_uid = int(uid_fields[1]) if len(uid_fields) >= 2 else -1
        except ValueError:
            process_uid = -1
        if process_name != "pipewire" or process_uid != os.getuid():
            continue
        task_root = process_path / "task"
        try:
            tasks = sorted(
                (path for path in task_root.iterdir() if path.name.isdigit()),
                key=lambda path: int(path.name),
            )
        except OSError:
            continue
        for task_path in tasks:
            try:
                thread_name = (task_path / "comm").read_text(encoding="utf-8").strip()
            except OSError:
                continue
            if not is_pipewire_data_loop(process_name, thread_name):
                continue
            loops.append(
                {
                    "process_pid": int(process_path.name),
                    "tid": int(task_path.name),
                    "thread_name": thread_name,
                }
            )
    return loops


def pipewire_data_loop_scheduling(
    loops: Sequence[dict[str, object]] | None = None,
) -> list[dict[str, object]]:
    """Snapshot scheduling for pre-discovered PipeWire server data loops."""
    identities = list(loops) if loops is not None else discover_pipewire_data_loops()
    snapshots = []
    for identity in identities:
        tid = int(identity["tid"])
        expected_name = str(identity["thread_name"])
        try:
            current_name = pathlib.Path(f"/proc/{tid}/comm").read_text(
                encoding="utf-8"
            ).strip()
        except OSError:
            current_name = "unavailable"
        if current_name != expected_name:
            telemetry: dict[str, object] = {
                "pid": tid,
                "state": "unavailable",
                "error": (
                    f"thread identity changed: expected {expected_name!r}, "
                    f"observed {current_name!r}"
                ),
            }
        else:
            telemetry = process_scheduling(tid)
        telemetry.update(identity)
        snapshots.append(telemetry)
    return snapshots


def validate_pipewire_data_loop_scheduling(
    scheduling: Sequence[dict[str, object]], required_count: int
) -> None:
    """Fail unless every pre-discovered server data loop remains measurable."""
    required_fields = {"policy", "priority", "nice", "runtime_ns", "wait_ns", "timeslices"}
    if len(scheduling) != required_count:
        raise SoakError(
            f"PipeWire data-loop count changed: {len(scheduling)} observed, "
            f"{required_count} required"
        )
    failures = [
        item
        for item in scheduling
        if item.get("state") != "running" or not required_fields.issubset(item)
    ]
    if failures:
        raise SoakError(
            "PipeWire data-loop scheduling became unavailable: "
            + json.dumps(failures, sort_keys=True)
        )


def prepare_rtkit_target() -> None:
    """Apply RTKit's bounded prerequisites in a transport helper before exec."""
    resource.setrlimit(
        resource.RLIMIT_RTTIME,
        (RTKIT_RTTIME_USEC, RTKIT_RTTIME_USEC),
    )
    reset_on_fork = getattr(os, "SCHED_RESET_ON_FORK", 0)
    if not reset_on_fork:
        raise RuntimeError("SCHED_RESET_ON_FORK is unavailable")
    os.sched_setscheduler(
        0,
        os.SCHED_OTHER | reset_on_fork,
        os.sched_param(0),
    )


def rtkit_command(pid: int, priority: int) -> list[str]:
    """Build the one bounded same-process/thread RTKit request."""
    return [
        "gdbus",
        "call",
        "--system",
        "--dest",
        RTKIT_SERVICE,
        "--object-path",
        RTKIT_PATH,
        "--method",
        RTKIT_METHOD,
        str(pid),
        str(pid),
        str(priority),
    ]


def validate_rtkit_scheduling(
    scheduling: dict[str, dict[str, object]], priority: int
) -> None:
    """Fail unless both ALSA helpers retain the exact RTKit A/B policy."""
    failures = []
    for name in ("playback_helper", "capture_helper"):
        observed = scheduling.get(name, {})
        expected = {
            "state": "running",
            "policy": "SCHED_RR",
            "priority": priority,
            "reset_on_fork": True,
        }
        for key, value in expected.items():
            if observed.get(key) != value:
                failures.append(f"{name}.{key}={observed.get(key)!r}, required {value!r}")
    if failures:
        raise SoakError("RTKit helper policy drift: " + "; ".join(failures))


def validate_one_rtkit_helper(
    name: str, scheduling: dict[str, object], priority: int
) -> None:
    expected = {
        "state": "running",
        "policy": "SCHED_RR",
        "priority": priority,
        "reset_on_fork": True,
    }
    failures = [
        f"{key}={scheduling.get(key)!r}, required {value!r}"
        for key, value in expected.items()
        if scheduling.get(key) != value
    ]
    if failures:
        raise SoakError(f"RTKit {name} policy mismatch: " + "; ".join(failures))


def promote_rtkit_helper(pid: int, priority: int) -> dict[str, object]:
    """Request one helper-thread promotion and prove its exact resulting policy."""
    before = process_scheduling(pid)
    if before.get("state") != "running" or not before.get("reset_on_fork"):
        raise SoakError(f"RTKit target prerequisites are absent for pid {pid}: {before}")
    try:
        completed = subprocess.run(
            rtkit_command(pid, priority),
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        detail = getattr(error, "stderr", "") or str(error)
        raise SoakError(f"RTKit promotion failed for pid {pid}: {detail.strip()}") from error
    after = process_scheduling(pid)
    validate_one_rtkit_helper(f"pid {pid}", after, priority)
    return {
        "pid": pid,
        "priority": priority,
        "reply": completed.stdout.strip(),
        "before": before,
        "after": after,
    }


def safe_hw_params() -> dict[str, dict[str, str]]:
    """Read both hardware geometries without masking the triggering failure."""
    observed: dict[str, dict[str, str]] = {}
    for direction, path in ALSA_HW_PARAM_PATHS.items():
        try:
            observed[direction] = parse_hw_params(path)
        except SoakError as error:
            observed[direction] = {"state": "unavailable", "error": str(error)}
    return observed


def helper_pids(
    playback: subprocess.Popen | None,
    capture: subprocess.Popen | None,
    capture_extractor: subprocess.Popen | None,
    pw_top: subprocess.Popen | None,
    writer_pid: int | None,
) -> dict[str, int]:
    processes = {
        "playback_helper": playback.pid if playback is not None else None,
        "capture_helper": capture.pid if capture is not None else None,
        "capture_extractor": capture_extractor.pid if capture_extractor is not None else None,
        "pw_top": pw_top.pid if pw_top is not None else None,
        "playback_feeder": writer_pid,
    }
    return {name: pid for name, pid in processes.items() if pid is not None}


def child_exit_observations(pids: dict[str, int]) -> dict[str, dict[str, object] | None]:
    """Return exit state for each helper while leaving every exited child waitable."""
    return {name: child_exit_status(pid) for name, pid in pids.items()}


def terminal_evidence(
    reason: str,
    start: float,
    transport: str,
    pipe_capacities: dict[str, int],
    playback: subprocess.Popen | None,
    capture: subprocess.Popen | None,
    capture_extractor: subprocess.Popen | None,
    pw_top: subprocess.Popen | None,
    writer_pid: int | None,
) -> dict[str, object]:
    """Capture terminal evidence before poll, wait, signal, or other teardown."""
    pids = helper_pids(playback, capture, capture_extractor, pw_top, writer_pid)
    alsa_evidence = None
    if transport == "alsa":
        # Read the volatile PCM view first: helpers may close their direction
        # immediately after a fatal xrun, while zombie /proc data remains.
        alsa_evidence = {
            "playback_status": alsa_status("playback"),
            "capture_status": alsa_status("capture"),
            "hw_params": safe_hw_params(),
        }
    evidence: dict[str, object] = {
        "reason": reason,
        "elapsed_seconds": round(time.monotonic() - start, 6),
        "transport": transport,
        "pipe_capacities": dict(pipe_capacities),
        "process_scheduling": {
            name: process_scheduling(pid) for name, pid in pids.items()
        },
        "process_threads": {
            name: process_threads_scheduling(pid) for name, pid in pids.items()
        },
        "child_exit_observations": child_exit_observations(pids),
        "irq_count": irq_count(),
    }
    if transport == "pipewire":
        evidence["pipewire_data_loops"] = pipewire_data_loop_scheduling()
    if alsa_evidence is not None:
        evidence["alsa"] = alsa_evidence
    return evidence


def write_forever(handle, payload: bytes) -> None:
    """Feed playback from an isolated process, away from analysis GIL stalls."""
    view = memoryview(payload)
    while True:
        offset = 0
        while offset < len(view):
            try:
                written = handle.write(view[offset:])
                handle.flush()
            except (BrokenPipeError, OSError):
                return
            if not written:
                return
            offset += written


def spawn_playback_feeder(handle, payload: bytes) -> int:
    """Fork a dedicated feeder and close the parent's copy of the pipe."""
    try:
        pid = os.fork()
    except OSError as error:
        raise SoakError(f"cannot fork playback feeder: {error}") from error
    if pid == 0:
        try:
            write_forever(handle, payload)
        finally:
            os._exit(0)
    handle.close()
    return pid


def terminate_playback_feeder(pid: int | None) -> int | None:
    if pid is None:
        return None
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        _, status = os.waitpid(pid, 0)
    except ChildProcessError:
        return None
    return status


def read_exact(handle, size: int, stop: threading.Event, timeout_seconds: float = 3.0) -> bytes:
    chunks = []
    remaining = size
    deadline = time.monotonic() + timeout_seconds
    descriptor = handle.fileno()
    while remaining and not stop.is_set():
        wait = deadline - time.monotonic()
        if wait <= 0:
            raise SoakError(f"capture stream stalled for {timeout_seconds:.1f} seconds")
        readable, _, _ = select.select([descriptor], [], [], min(wait, 0.5))
        if not readable:
            continue
        chunk = os.read(descriptor, remaining)
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def save_event(output_dir: pathlib.Path, sequence: int, payload: bytes, analysis: Analysis) -> str:
    name = f"event-{sequence:05d}-{analysis.event}-{analysis.phase_delta:+d}.s32le"
    path = output_dir / name
    path.write_bytes(payload)
    return name


def parse_pw_top_row(decoded: str, nodes: dict) -> dict[str, object] | None:
    """Parse one running pw-top row for the exact test nodes or helpers."""
    fields = decoded.split()
    if len(fields) < 13 or fields[0] != "R":
        return None
    name = " ".join(fields[12:])
    normalized_name = name.removeprefix("+ ")
    roles = {
        nodes["playback"]["name"]: "playback_node",
        nodes["capture"]["name"]: "capture_node",
        "pw-play": "playback_helper",
        "pw-record": "capture_helper",
    }
    role = roles.get(normalized_name)
    if role is None:
        return None
    try:
        return {
            "role": role,
            "node_id": int(fields[1]),
            "quantum": int(fields[2]),
            "rate": int(fields[3]),
            "wait": fields[4],
            "busy": fields[5],
            "wait_quantum_ratio": float(fields[6]),
            "busy_quantum_ratio": float(fields[7]),
            "errors": int(fields[8]),
            "format": fields[9],
            "channels": int(fields[10]),
            "format_rate": int(fields[11]),
            "name": normalized_name,
        }
    except ValueError:
        return None


class PipeWireErrorTracker:
    """Emit one record for initial ERR state and every observed counter change."""

    def __init__(self) -> None:
        self.errors: dict[str, int] = {}

    def update(self, row: dict[str, object]) -> dict[str, object] | None:
        role = str(row["role"])
        current = int(row["errors"])
        previous = self.errors.get(role)
        if previous == current:
            return None
        self.errors[role] = current
        transition = dict(row)
        transition.update(
            {
                "previous_errors": previous,
                "error_delta": None if previous is None else current - previous,
            }
        )
        return transition


def filter_pw_top(
    handle,
    path: pathlib.Path,
    error_path: pathlib.Path,
    nodes: dict,
    stop: threading.Event,
) -> None:
    markers = ("quantum", "p2626", "pw-play", "pw-record", "loopback")
    tracker = PipeWireErrorTracker()
    try:
        with (
            path.open("x", encoding="utf-8", buffering=1) as output,
            error_path.open("x", encoding="utf-8", buffering=1) as error_output,
        ):
            while not stop.is_set():
                line = handle.readline()
                if not line:
                    return
                decoded = line.decode("utf-8", errors="replace").rstrip()
                if any(marker in decoded.lower() for marker in markers):
                    output.write(f"{utc_now()} {decoded}\n")
                row = parse_pw_top_row(decoded, nodes)
                if row is not None:
                    transition = tracker.update(row)
                    if transition is not None:
                        json_line(
                            error_output,
                            "pipewire_error_transition",
                            **transition,
                        )
    except OSError:
        stop.set()


def terminate(process: subprocess.Popen | None) -> None:
    if process is None or process.poll() is not None:
        return
    process.send_signal(signal.SIGINT)
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=2)


def stream_commands(transport: str, nodes: dict) -> tuple[list[str], list[str]]:
    if transport == "pipewire":
        return (
            [
                "pw-play",
                "--target",
                nodes["playback"]["name"],
                "--rate",
                str(RATE),
                "--channels",
                "2",
                "--channel-map",
                "FL,FR",
                "--format",
                "s32",
                "--latency",
                "256",
                "-",
            ],
            [
                "pw-record",
                "--target",
                nodes["capture"]["name"],
                "--rate",
                str(RATE),
                "--channels",
                "1",
                "--channel-map",
                "MONO",
                "--format",
                "s32",
                "--latency",
                "256",
                "-",
            ],
        )
    if transport == "alsa":
        common = [
            "--quiet",
            "--device",
            ALSA_DEVICE,
            "--file-type",
            "raw",
            "--format",
            "S32_LE",
            "--rate",
            str(RATE),
            "--channels",
            str(HARDWARE_CHANNELS),
            "--period-size",
            str(PERIOD_FRAMES),
            "--buffer-size",
            str(BUFFER_FRAMES),
            "--mmap",
            "--fatal-errors",
            "-",
        ]
        return (["aplay", *common], ["arecord", *common])
    raise SoakError(f"unsupported transport: {transport}")


def run_soak(args: argparse.Namespace) -> None:
    if args.live_ack != LIVE_ACK:
        raise SoakError(f"live run requires --live-ack {LIVE_ACK}")
    if not (-50.0 <= args.level_dbfs <= -20.0):
        raise SoakError("level must remain between -50 and -20 dBFS")
    if args.duration_seconds < 30 or args.duration_seconds > 12 * 60 * 60:
        raise SoakError("duration must be between 30 seconds and 12 hours")
    if args.max_events < 1 or args.max_events > 10_000:
        raise SoakError("max-events must be between 1 and 10000")
    if args.rtkit_helper_priority:
        if args.transport != "alsa":
            raise SoakError("RTKit helper promotion is only valid for direct ALSA")
        if not 1 <= args.rtkit_helper_priority <= RTKIT_MAX_PRIORITY:
            raise SoakError(
                f"RTKit helper priority must be between 1 and {RTKIT_MAX_PRIORITY}"
            )
    transport_executables = ("pw-play", "pw-record") if args.transport == "pipewire" else (
        "aplay",
        "arecord",
    )
    extra_executables = ("gdbus",) if args.rtkit_helper_priority else ()
    for executable in (*transport_executables, "pw-dump", "pw-top", *extra_executables):
        if shutil.which(executable) is None:
            raise SoakError(f"required executable is absent: {executable}")

    output_dir = pathlib.Path(args.output_dir).expanduser().resolve()
    if output_dir.exists():
        raise SoakError(f"output directory already exists: {output_dir}")
    output_dir.mkdir(parents=True, mode=0o700)
    if shutil.disk_usage(output_dir).free < 512 * 1024 * 1024:
        raise SoakError("less than 512 MiB free at output location")

    nodes = inspect_nodes(args.capture_fragment)
    pipewire_loop_identities = (
        discover_pipewire_data_loops() if args.transport == "pipewire" else []
    )
    initial_pipewire_data_loops = (
        pipewire_data_loop_scheduling(pipewire_loop_identities)
        if args.transport == "pipewire"
        else []
    )
    if args.transport == "pipewire" and not initial_pipewire_data_loops:
        raise SoakError("cannot identify any PipeWire server data-loop thread")
    if args.transport == "pipewire":
        validate_pipewire_data_loop_scheduling(
            initial_pipewire_data_loops, len(pipewire_loop_identities)
        )
    reference = make_reference()
    playback_channels = 2 if args.transport == "pipewire" else HARDWARE_CHANNELS
    playback_channel = 0 if args.transport == "pipewire" else DIRECT_CHANNEL_INDEX
    playback_bytes = interleaved_playback_period(
        reference, args.level_dbfs, playback_channels, playback_channel
    )
    playback_command, capture_command = stream_commands(args.transport, nodes)
    playback_stderr = "pw-play.stderr" if args.transport == "pipewire" else "aplay.stderr"
    capture_stderr = "pw-record.stderr" if args.transport == "pipewire" else "arecord.stderr"
    tracker = PhaseTracker(reference)
    log_path = output_dir / "events.jsonl"
    summary_path = output_dir / "summary.json"
    stop = threading.Event()
    playback: subprocess.Popen | None = None
    capture: subprocess.Popen | None = None
    capture_extractor: subprocess.Popen | None = None
    capture_stream = None
    pipe_capacities: dict[str, int] = {}
    rtkit_promotions: dict[str, dict[str, object]] = {}
    capture_pipe_read: int | None = None
    capture_pipe_write: int | None = None
    extractor_ready_read: int | None = None
    extractor_ready_write: int | None = None
    pw_top: subprocess.Popen | None = None
    writer_pid: int | None = None
    pw_top_writer: threading.Thread | None = None
    event_count = 0
    loss_episodes = 0
    recoveries = 0
    max_loss_blocks = 0
    blocks = 0
    min_correlation = 1.0
    max_peak_dbfs = -300.0
    start = time.monotonic()
    terminal_result = "failed"
    terminal_reason = "unclassified"
    terminal_snapshot_recorded = False
    terminal_snapshot_error: str | None = None
    teardown_returncodes: dict[str, int | None] = {}
    capture_pipeline_ready = False
    pipewire_error_tracking_started = False
    scheduling_telemetry_started = False

    try:
        with log_path.open("x", encoding="utf-8", buffering=1) as log:
            json_line(
                log,
                "start",
                nodes=nodes,
                rate=RATE,
                hardware_channels=HARDWARE_CHANNELS,
                period_frames=PERIOD_FRAMES,
                buffer_frames=BUFFER_FRAMES,
                reference_frames=REFERENCE_FRAMES,
                analysis_frames=ANALYSIS_FRAMES,
                level_dbfs=args.level_dbfs,
                duration_seconds=args.duration_seconds,
                capture_fragment=args.capture_fragment,
                transport=args.transport,
                alsa_device=ALSA_DEVICE if args.transport == "alsa" else None,
                direct_channel_index=DIRECT_CHANNEL_INDEX if args.transport == "alsa" else None,
                rtkit_helper_priority=args.rtkit_helper_priority or None,
                rtkit_rttime_usec=(
                    RTKIT_RTTIME_USEC if args.rtkit_helper_priority else None
                ),
                capture_pipeline_mode="isolated_extractor",
                capture_pipe_required_bytes=PIPE_BYTES,
                pipewire_data_loops=initial_pipewire_data_loops,
            )

            pw_top = subprocess.Popen(
                ["pw-top", "--batch-mode"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=(output_dir / "pw-top.stderr").open("xb"),
                bufsize=0,
            )
            if pw_top.stdout is None:
                raise SoakError("failed to create pw-top telemetry pipe")

            try:
                playback = subprocess.Popen(
                    playback_command,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL,
                    stderr=(output_dir / playback_stderr).open("xb"),
                    bufsize=0,
                    preexec_fn=(
                        prepare_rtkit_target if args.rtkit_helper_priority else None
                    ),
                )
            except (OSError, subprocess.SubprocessError) as error:
                raise SoakError(f"cannot start playback helper: {error}") from error
            if args.rtkit_helper_priority:
                rtkit_promotions["playback_helper"] = promote_rtkit_helper(
                    playback.pid, args.rtkit_helper_priority
                )
            if playback.stdin is None:
                raise SoakError("failed to create playback pipe")
            if args.transport == "alsa":
                pipe_capacities["playback_input"] = set_pipe_capacity(playback.stdin)
            # Fork before starting the telemetry thread. The feeder must not
            # share the analysis interpreter's GIL or fork a threaded process.
            writer_pid = spawn_playback_feeder(playback.stdin, playback_bytes)
            time.sleep(0.25)
            capture_channels, capture_channel = capture_extractor_geometry(args.transport)
            capture_pipe_read, capture_pipe_write = os.pipe()
            pipe_capacities["capture_raw"] = set_pipe_capacity(capture_pipe_write)
            extractor_ready_read, extractor_ready_write = os.pipe()
            capture_extractor = subprocess.Popen(
                [
                    sys.executable,
                    str(pathlib.Path(__file__).resolve()),
                    "extract-channel",
                    "--channels",
                    str(capture_channels),
                    "--channel-index",
                    str(capture_channel),
                    "--block-frames",
                    str(ANALYSIS_FRAMES),
                    "--ready-fd",
                    str(extractor_ready_write),
                ],
                stdin=capture_pipe_read,
                stdout=subprocess.PIPE,
                stderr=(output_dir / "capture-extractor.stderr").open("xb"),
                pass_fds=(extractor_ready_write,),
                bufsize=0,
            )
            os.close(capture_pipe_read)
            capture_pipe_read = None
            os.close(extractor_ready_write)
            extractor_ready_write = None
            wait_for_extractor_ready(capture_extractor, extractor_ready_read)
            os.close(extractor_ready_read)
            extractor_ready_read = None
            try:
                try:
                    capture = subprocess.Popen(
                        capture_command,
                        stdin=subprocess.DEVNULL,
                        stdout=capture_pipe_write,
                        stderr=(output_dir / capture_stderr).open("xb"),
                        bufsize=0,
                        preexec_fn=(
                            prepare_rtkit_target if args.rtkit_helper_priority else None
                        ),
                    )
                except (OSError, subprocess.SubprocessError) as error:
                    raise SoakError(f"cannot start capture helper: {error}") from error
                if args.rtkit_helper_priority:
                    rtkit_promotions["capture_helper"] = promote_rtkit_helper(
                        capture.pid, args.rtkit_helper_priority
                    )
            finally:
                os.close(capture_pipe_write)
                capture_pipe_write = None
            if capture_extractor.stdout is None:
                raise SoakError("failed to create capture extractor pipe")
            pipe_capacities["capture_mono"] = set_pipe_capacity(capture_extractor.stdout)
            capture_stream = capture_extractor.stdout
            capture_pipeline_ready = True
            pw_top_writer = threading.Thread(
                target=filter_pw_top,
                args=(
                    pw_top.stdout,
                    output_dir / "pw-top.filtered.log",
                    output_dir / "pw-errors.jsonl",
                    nodes,
                    stop,
                ),
                daemon=True,
            )
            pw_top_writer.start()
            pipewire_error_tracking_started = args.transport == "pipewire"
            pipeline_pids = helper_pids(
                playback, capture, capture_extractor, pw_top, writer_pid
            )
            pipeline_pids.pop("pw_top", None)
            pipeline_scheduling = {
                name: process_scheduling(pid) for name, pid in pipeline_pids.items()
            }
            pipeline_threads = {
                name: process_threads_scheduling(pid) for name, pid in pipeline_pids.items()
            }
            validate_process_threads_scheduling(pipeline_threads)
            pipeline_data_loops = (
                pipewire_data_loop_scheduling(pipewire_loop_identities)
                if args.transport == "pipewire"
                else []
            )
            if args.transport == "pipewire":
                validate_pipewire_data_loop_scheduling(
                    pipeline_data_loops, len(pipewire_loop_identities)
                )
            if args.rtkit_helper_priority:
                validate_rtkit_scheduling(pipeline_scheduling, args.rtkit_helper_priority)
            json_line(
                log,
                "pipeline_ready",
                pipe_capacities=pipe_capacities,
                process_scheduling=pipeline_scheduling,
                process_threads=pipeline_threads,
                pipewire_data_loops=pipeline_data_loops,
                rtkit_promotions=rtkit_promotions,
            )
            scheduling_telemetry_started = True
            geometry = wait_for_geometry(playback, capture)
            json_line(log, "geometry", values=geometry)

            block_bytes = ANALYSIS_FRAMES * 4
            next_telemetry = time.monotonic()
            acquired = False
            acquire_deadline = time.monotonic() + 10.0
            while time.monotonic() - start < args.duration_seconds:
                pids = helper_pids(
                    playback,
                    capture,
                    capture_extractor,
                    pw_top,
                    writer_pid,
                )
                exit_observations = child_exit_observations(pids)
                exited = {
                    name: observation
                    for name, observation in exit_observations.items()
                    if observation is not None
                }
                if exited:
                    raise SoakError(
                        "required process exited without reap: "
                        + json.dumps(exited, sort_keys=True)
                    )
                payload = read_exact(capture_stream, block_bytes, stop)
                if len(payload) != block_bytes:
                    raise SoakError(
                        f"short capture block: {len(payload)} of {block_bytes} bytes"
                    )
                samples = decode_s32le(payload)
                peak = max(abs(value) for value in samples)
                if peak >= 0.95:
                    raise SoakError(f"capture clipping guard tripped at {peak:.6f} FS")
                rms = math.sqrt(sum(value * value for value in samples) / len(samples))
                if not acquired:
                    if rms < dbfs_to_linear(-60.0):
                        if time.monotonic() >= acquire_deadline:
                            raise SoakError("no usable loopback signal within ten seconds")
                        continue
                    acquired = True

                analysis = tracker.analyze(samples)
                blocks += 1
                min_correlation = min(min_correlation, abs(analysis.correlation))
                max_peak_dbfs = max(max_peak_dbfs, analysis.peak_dbfs)
                if blocks == 1 and abs(analysis.correlation) < 0.45:
                    raise SoakError(
                        f"initial loopback correlation too low: {analysis.correlation:.6f}"
                    )
                if analysis.event:
                    event_count += 1
                    if analysis.event == "correlation_drop":
                        loss_episodes += 1
                    filename = save_event(output_dir, event_count, payload, analysis)
                    json_line(
                        log,
                        "continuity_event",
                        sequence=event_count,
                        event=analysis.event,
                        phase_delta_frames=analysis.phase_delta,
                        correlation=round(analysis.correlation, 8),
                        rms_dbfs=round(analysis.rms_dbfs, 4),
                        peak_dbfs=round(analysis.peak_dbfs, 4),
                        capture_file=filename,
                        lock_status=analysis.lock_status,
                        loss_blocks=analysis.loss_blocks,
                    )
                    if event_count >= args.max_events:
                        raise SoakError(f"continuity event limit reached: {args.max_events}")
                if analysis.lock_status == "recovered":
                    recoveries += 1
                    json_line(
                        log,
                        "continuity_recovery",
                        after_event_sequence=event_count,
                        loss_blocks=analysis.loss_blocks,
                        phase_delta_frames=analysis.phase_delta,
                        correlation=round(analysis.correlation, 8),
                    )
                max_loss_blocks = max(max_loss_blocks, analysis.loss_blocks)
                if (
                    analysis.lock_status == "lost"
                    and analysis.loss_blocks >= MAX_CONSECUTIVE_LOST_BLOCKS
                ):
                    raise SoakError(
                        "global phase lock not recovered within "
                        f"{MAX_CONSECUTIVE_LOST_BLOCKS} analysis blocks"
                    )

                now = time.monotonic()
                if now >= next_telemetry:
                    playback_status = alsa_status("playback")
                    capture_status = alsa_status("capture")
                    for direction, status in (
                        ("playback", playback_status),
                        ("capture", capture_status),
                    ):
                        state = status.get("state") if status else None
                        if state != "RUNNING":
                            raise SoakError(
                                f"ALSA {direction} left RUNNING state: {state!r}"
                            )
                    telemetry = {
                        "elapsed_seconds": round(now - start, 3),
                        "blocks": blocks,
                        "events": event_count,
                        "correlation": round(analysis.correlation, 8),
                        "phase_delta_frames": analysis.phase_delta,
                        "lock_status": analysis.lock_status,
                        "loss_blocks": analysis.loss_blocks,
                        "rms_dbfs": round(analysis.rms_dbfs, 4),
                        "peak_dbfs": round(analysis.peak_dbfs, 4),
                        "irq_count": irq_count(),
                        "playback_status": playback_status,
                        "capture_status": capture_status,
                    }
                    telemetry_pids = helper_pids(
                        playback, capture, capture_extractor, pw_top, writer_pid
                    )
                    telemetry_pids.pop("pw_top", None)
                    scheduling = {
                        name: process_scheduling(pid)
                        for name, pid in telemetry_pids.items()
                    }
                    telemetry["process_scheduling"] = scheduling
                    telemetry["process_threads"] = {
                        name: process_threads_scheduling(pid)
                        for name, pid in telemetry_pids.items()
                    }
                    validate_process_threads_scheduling(telemetry["process_threads"])
                    if args.transport == "pipewire":
                        data_loops = pipewire_data_loop_scheduling(
                            pipewire_loop_identities
                        )
                        validate_pipewire_data_loop_scheduling(
                            data_loops, len(pipewire_loop_identities)
                        )
                        telemetry["pipewire_data_loops"] = data_loops
                    if args.rtkit_helper_priority:
                        validate_rtkit_scheduling(scheduling, args.rtkit_helper_priority)
                    json_line(
                        log,
                        "telemetry",
                        **telemetry,
                    )
                    next_telemetry = now + 1.0
                    validate_geometry()
                    if shutil.disk_usage(output_dir).free < 256 * 1024 * 1024:
                        raise SoakError("disk free space fell below 256 MiB")

            terminal_result = "pass" if event_count == 0 else "events_observed"
            terminal_reason = "duration_complete"
            json_line(
                log,
                "stop",
                result=terminal_result,
                reason=terminal_reason,
                elapsed_seconds=round(time.monotonic() - start, 3),
                blocks=blocks,
                events=event_count,
                min_abs_correlation=round(min_correlation, 8),
                max_peak_dbfs=round(max_peak_dbfs, 4),
                loss_episodes=loss_episodes,
                recoveries=recoveries,
                max_loss_blocks=max_loss_blocks,
            )
    except (KeyboardInterrupt, SoakError) as error:
        terminal_reason = "interrupted" if isinstance(error, KeyboardInterrupt) else str(error)
        try:
            with log_path.open("a", encoding="utf-8", buffering=1) as log:
                json_line(
                    log,
                    "terminal_snapshot",
                    **terminal_evidence(
                        terminal_reason,
                        start,
                        args.transport,
                        pipe_capacities,
                        playback,
                        capture,
                        capture_extractor,
                        pw_top,
                        writer_pid,
                    ),
                )
            terminal_snapshot_recorded = True
        except Exception as snapshot_error:
            # Terminal evidence must never replace the failure it is trying to
            # explain. The summary retains this bounded instrumentation error.
            terminal_snapshot_error = str(snapshot_error)
        raise
    finally:
        stop.set()
        for descriptor in (
            capture_pipe_read,
            capture_pipe_write,
            extractor_ready_read,
            extractor_ready_write,
        ):
            if descriptor is not None:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
        terminate(playback)
        terminate(capture)
        terminate(capture_extractor)
        terminate(pw_top)
        feeder_status = terminate_playback_feeder(writer_pid)
        if pw_top_writer is not None:
            pw_top_writer.join(timeout=2)
        teardown_returncodes = {
            "playback_helper": playback.returncode if playback is not None else None,
            "capture_helper": capture.returncode if capture is not None else None,
            "capture_extractor": (
                capture_extractor.returncode if capture_extractor is not None else None
            ),
            "pw_top": pw_top.returncode if pw_top is not None else None,
            "playback_feeder_wait_status": feeder_status,
        }
        try:
            with log_path.open("a", encoding="utf-8", buffering=1) as log:
                json_line(
                    log,
                    "teardown_complete",
                    reason=terminal_reason,
                    elapsed_seconds=round(time.monotonic() - start, 6),
                    returncodes=teardown_returncodes,
                )
        except OSError as teardown_log_error:
            if terminal_snapshot_error is None:
                terminal_snapshot_error = f"cannot append teardown evidence: {teardown_log_error}"
        summary = {
            "result": terminal_result,
            "reason": terminal_reason,
            "elapsed_seconds": round(time.monotonic() - start, 3),
            "blocks": blocks,
            "events": event_count,
            "min_abs_correlation": round(min_correlation, 8) if blocks else None,
            "max_peak_dbfs": round(max_peak_dbfs, 4) if blocks else None,
            "loss_episodes": loss_episodes,
            "recoveries": recoveries,
            "max_loss_blocks": max_loss_blocks,
            "output_dir": str(output_dir),
            "transport": args.transport,
            "capture_pipeline_isolated": capture_pipeline_ready,
            "capture_pipe_required_bytes": PIPE_BYTES,
            "pipewire_error_transitions_recorded": pipewire_error_tracking_started,
            "scheduling_telemetry_recorded": scheduling_telemetry_started,
            "rtkit_helper_priority": args.rtkit_helper_priority or None,
            "time_utc": utc_now(),
            "terminal_snapshot_recorded": terminal_snapshot_recorded,
            "terminal_snapshot_error": terminal_snapshot_error,
            "teardown_returncodes": teardown_returncodes,
        }
        summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def duration_seconds(value: str) -> int:
    if value.isdigit():
        return int(value)
    fields = value.split(":")
    if len(fields) not in (2, 3) or not all(field.isdigit() for field in fields):
        raise argparse.ArgumentTypeError("duration must be seconds, MM:SS, or HH:MM:SS")
    numbers = [int(field) for field in fields]
    if len(numbers) == 2:
        minutes, seconds = numbers
        hours = 0
    else:
        hours, minutes, seconds = numbers
    if minutes >= 60 or seconds >= 60:
        raise argparse.ArgumentTypeError("duration minutes and seconds must be below 60")
    return hours * 3600 + minutes * 60 + seconds


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    commands.add_parser("self-test", help="run offline clean and injected-fault fixtures")
    extract = commands.add_parser("extract-channel", help=argparse.SUPPRESS)
    extract.add_argument("--channels", type=int, required=True)
    extract.add_argument("--channel-index", type=int, required=True)
    extract.add_argument("--block-frames", type=int, required=True)
    extract.add_argument("--ready-fd", type=int, default=None, help=argparse.SUPPRESS)
    replay = commands.add_parser(
        "replay", help="read-only global classification of retained events"
    )
    replay.add_argument("--artifact-dir", required=True)
    inspect = commands.add_parser("inspect", help="read and validate the two exact PipeWire nodes")
    inspect.add_argument("--capture-fragment", default=CAPTURE_FRAGMENT)
    run = commands.add_parser("run", help="open the exact nodes and perform a live soak")
    run.add_argument("--duration", dest="duration_seconds", type=duration_seconds, required=True)
    run.add_argument("--output-dir", required=True)
    run.add_argument("--level-dbfs", type=float, default=-30.0)
    run.add_argument("--max-events", type=int, default=1_000)
    run.add_argument("--capture-fragment", default=CAPTURE_FRAGMENT)
    run.add_argument("--transport", choices=("pipewire", "alsa"), default="pipewire")
    run.add_argument("--rtkit-helper-priority", type=int, default=0)
    run.add_argument("--live-ack", required=True)
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "self-test":
            run_self_test()
        elif args.command == "extract-channel":
            extract_channel_stream(
                sys.stdin.buffer,
                sys.stdout.buffer,
                args.channels,
                args.channel_index,
                args.block_frames,
                args.ready_fd,
            )
        elif args.command == "replay":
            print(json.dumps(replay_artifacts(pathlib.Path(args.artifact_dir)), sort_keys=True))
        elif args.command == "inspect":
            print(json.dumps(inspect_nodes(args.capture_fragment), indent=2, sort_keys=True))
        elif args.command == "run":
            run_soak(args)
        else:
            raise SoakError(f"unknown command: {args.command}")
    except SoakError as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("FAIL: interrupted", file=sys.stderr)
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
