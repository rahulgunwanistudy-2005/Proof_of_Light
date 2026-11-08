"""Vectorized physics spike. All thresholds provisional until held-out physical eval.

Array contract: uint8 frames [time, y, x, RGB], times and paint_ms in milliseconds
on the same performance.now() clock relative to capture start. Camera callback
timestamps are presentation times; latency search absorbs camera/display delay.
No client timestamp or frame is trusted as hardware attestation.
"""

import math
import time

import numpy as np
from scipy.ndimage import median_filter

from .challenge import BODY_COLORS

VERSION = "spike-1-provisional"
THRESHOLDS = {
    "response_chroma": 0.004,
    "pixel_correlation": 0.35,
    "correlation": 0.65,
    "min_fps": 12,
    "max_duplicate_fraction": 0.35,
    "max_gap_ms": 300,
    "chance_p": 1e-6,
}


def chance_probability(k: int, n: int = 10) -> float:
    """I.i.d. uniform guessing null only; NOT the probability of fraud."""
    return sum(math.comb(n, j) * 0.25**j * 0.75 ** (n - j) for j in range(k, n + 1))


def _correlation(a, b) -> float:
    a = a - a.mean(axis=0)
    b = b - b.mean(axis=0)
    denominator = np.linalg.norm(a) * np.linalg.norm(b)
    return float(np.sum(a * b) / denominator) if denominator > 1e-12 else 0.0


def verify(frames: np.ndarray, times_ms: np.ndarray, paint_ms: np.ndarray, challenge: dict) -> dict:
    started = time.perf_counter()
    times = np.asarray(times_ms, dtype=float)
    paint = np.asarray(paint_ms, dtype=float)
    colors = challenge["calibration"] + challenge["body"]
    if len(challenge["body"]) != 10 or len(set(challenge["calibration"])) != 6:
        raise ValueError("Expected six calibration slots and ten body slots")
    if frames.dtype != np.uint8 or frames.ndim != 4 or frames.shape[-1] != 3:
        raise ValueError("Frames must be uint8 [time, height, width, RGB]")
    if len(frames) != len(times) or len(times) < 2 or len(paint) != len(colors) + 1:
        raise ValueError("Incomplete frames, timestamps or paint log")
    if not np.isfinite(times).all() or not np.isfinite(paint).all():
        raise ValueError("Timestamps must be finite")
    dt = np.diff(times)
    slot = float(challenge["slot_ms"])
    if slot < 400 or any(c not in challenge["palette"] for c in colors):
        raise ValueError("Invalid challenge palette or slot duration")
    fps = 1000 / np.median(dt) if np.all(dt > 0) else 0
    duplicates = float(np.mean(np.all(frames[1:] == frames[:-1], axis=(1, 2, 3))))
    integrity_errors = []
    if not np.all(dt > 0):
        integrity_errors.append("Frame timestamps are not strictly increasing")
    if fps < THRESHOLDS["min_fps"]:
        integrity_errors.append("Frame rate is too low")
    if dt.max() > THRESHOLDS["max_gap_ms"]:
        integrity_errors.append("Camera frame gap exceeds 300 ms")
    if duplicates > THRESHOLDS["max_duplicate_fraction"]:
        integrity_errors.append("Too many identical consecutive frames")
    # Never catch up missed paints in a burst: the client spaces from actual callbacks.
    if np.any(np.diff(paint) < slot - 2) or np.any(np.diff(paint) > slot * 1.5):
        integrity_errors.append("Screen timing was interrupted or changed too quickly")
    if times[0] > paint[0] + slot * 0.25:
        integrity_errors.append("Camera recording started after calibration began")
    if times[-1] < paint[prelude_end := len(challenge["calibration"])] + 500:
        integrity_errors.append("Camera recording did not cover calibration and challenge")
    result = {
        "version": VERSION,
        "thresholds": THRESHOLDS,
        "verdict": "FAILED" if integrity_errors else "INCONCLUSIVE",
        "reason": "; ".join(integrity_errors) or "Not enough light response to decode the sequence",
        "matches": 0,
        "slots": 10,
        "decoded": [None] * 10,
        "expected": challenge["body"],
        "chance_p": 1.0,
        "correlation": 0.0,
        "latency_ms": None,
        "response_strength": 0.0,
        "roi_fraction": 0.0,
        "integrity": {
            "fps": round(float(fps), 2),
            "duplicate_fraction": duplicates,
            "max_gap_ms": float(dt.max()),
            "errors": integrity_errors,
        },
        "order_bound": False,
        "money_movement_allowed": False,
        "limitations": [
            "Experimental thresholds; no physical gate passed yet",
            "A printed photo may reflect the correct live sequence",
            "Client-controlled frames and timings do not prove trusted camera capture",
            "Chance p assumes independent uniform guesses; it is not a fraud probability",
        ],
        "trace": [],
        "heatmap": [],
    }
    if integrity_errors:
        result["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 2)
        return result

    # Fixed grid bounds memory and makes the spike feasible on modest CPUs.
    step_y, step_x = max(1, frames.shape[1] // 60), max(1, frames.shape[2] // 80)
    rgb = frames[:, ::step_y, ::step_x].astype(np.float32) / 255
    chroma = rgb[..., :2] / np.maximum(rgb.sum(axis=-1, keepdims=True), 0.02)
    trace_all = np.mean(chroma, axis=(1, 2))
    expected_rgb = np.array([challenge["palette"][c] for c in colors], dtype=float)
    expected_chroma = expected_rgb[:, :2] / expected_rgb.sum(axis=1, keepdims=True)

    # Alignment uses calibration only. Never choose latency/ROI on secret matches.
    best_score, latency = -1.0, 0
    prelude_count = prelude_end
    for lag in range(0, 501, 10):
        indices = np.searchsorted(paint, times - lag, side="right") - 1
        valid = (indices >= 0) & (indices < prelude_count)
        if valid.sum() < 15:
            continue
        score = _correlation(trace_all[valid], expected_chroma[indices[valid]])
        if score > best_score:
            best_score, latency = score, lag
    result["latency_ms"] = latency
    indices = np.searchsorted(paint, times - latency, side="right") - 1
    calibration_frames = (indices >= 0) & (indices < prelude_count)
    reference = expected_chroma[indices[calibration_frames]]
    centered_ref = reference - reference.mean(axis=0)
    signal = chroma[calibration_frames]
    signal = signal - signal.mean(axis=0)
    strength = np.sqrt(np.mean(np.sum(signal**2, axis=-1), axis=0))
    numerator = np.einsum("tyxc,tc->yx", signal, centered_ref)
    denominator = np.sqrt(np.sum(signal**2, axis=(0, 3)) * np.sum(centered_ref**2))
    correlation_map = numerator / np.maximum(denominator, 1e-12)
    unclipped = np.mean(np.all((rgb > 0.02) & (rgb < 0.98), axis=-1), axis=0) > 0.90
    responsive = (
        (strength > THRESHOLDS["response_chroma"])
        & (correlation_map > THRESHOLDS["pixel_correlation"])
        & unclipped
    )
    heatmap = np.where(unclipped, np.maximum(correlation_map, 0) * strength, 0)
    result["heatmap"] = np.round(heatmap, 5).tolist()
    if responsive.sum() >= max(12, responsive.size * 0.005):
        score = heatmap[responsive]
        roi = responsive & (heatmap >= np.percentile(score, 50))
        result["roi_fraction"] = round(float(roi.mean()), 4)
        result["response_strength"] = float(np.median(strength[roi]))
        raw_trace = chroma[:, roi].mean(axis=1)
        # Rolling-median baseline suppresses slow AWB drift. Centroids are learned
        # from raw prelude; shift by local baseline change before classification.
        window = max(3, round(fps * 1.5) | 1)
        baseline = median_filter(raw_trace, size=(window, 1), mode="nearest")
        centers, base_centers = {}, {}
        for i, color in enumerate(challenge["calibration"]):
            mask = (times >= paint[i] + latency + slot * 0.25) & (
                times < paint[i + 1] + latency - slot * 0.15
            )
            if mask.sum() >= 2:
                centers[color] = np.median(raw_trace[mask], axis=0)
                base_centers[color] = np.median(baseline[mask], axis=0)
        if all(c in centers for c in BODY_COLORS):
            palette = np.array([centers[c] for c in BODY_COLORS])
            base_anchor = np.mean([base_centers[c] for c in BODY_COLORS], axis=0)
            decoded = []
            template, received = [], []
            for j in range(10):
                i = j + prelude_count
                mask = (times >= paint[i] + latency + slot * 0.25) & (
                    times < paint[i + 1] + latency - slot * 0.15
                )
                if mask.sum() < 2:
                    decoded.append(None)
                    continue
                # Baseline correction is deliberately conservative until eval.
                drift = np.median(baseline[mask], axis=0) - base_anchor
                value = np.median(raw_trace[mask], axis=0) - drift * 0.25
                decoded.append(BODY_COLORS[int(np.argmin(np.linalg.norm(palette - value, axis=1)))])
                template.append(centers[challenge["body"][j]])
                received.append(value)
            k = sum(a == b for a, b in zip(decoded, challenge["body"]))
            corr = _correlation(np.asarray(received), np.asarray(template)) if received else 0.0
            p = chance_probability(k)
            if None in decoded:
                verdict, reason = "INCONCLUSIVE", "Some screen slots have too few camera frames"
            elif p < THRESHOLDS["chance_p"] and corr >= THRESHOLDS["correlation"]:
                verdict, reason = (
                    "VERIFIED",
                    "The sampled surface followed the issued light sequence",
                )
            elif k >= 8:
                verdict, reason = (
                    "INCONCLUSIVE",
                    "Most slots matched, but the strict threshold was not met",
                )
            else:
                verdict, reason = (
                    "FAILED",
                    "A light response was present but did not match the issued sequence",
                )
            result.update(
                verdict=verdict,
                reason=reason,
                matches=k,
                decoded=decoded,
                chance_p=p,
                correlation=corr,
            )
        result["trace"] = [
            {"t_ms": round(float(t), 1), "r": round(float(c[0]), 5), "g": round(float(c[1]), 5)}
            for t, c in zip(times, raw_trace)
        ]
    result["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 2)
    return result
