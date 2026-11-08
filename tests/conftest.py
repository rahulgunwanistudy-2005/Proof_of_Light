import numpy as np
import pytest
from pol_verifier.challenge import BODY_COLORS, CALIBRATION, PALETTE


def synthetic_capture(*, latency=120, response=0.55, drift=0, seed=7, replay=False):
    """Numerical signal test, never a physical capture or fraud-detector eval."""
    rng = np.random.default_rng(seed)
    body = ["red", "green", "yellow", "blue", "red", "yellow", "green", "blue", "yellow", "red"]
    challenge = {"calibration": CALIBRATION, "body": body, "palette": PALETTE, "slot_ms": 400}
    paint = 500 + np.arange(17) * 400
    times = np.arange(0, paint[-1] + 600, 1000 / 30)
    rendered_body = [BODY_COLORS[(BODY_COLORS.index(c) + 1) % 4] for c in body] if replay else body
    colors = CALIBRATION + rendered_body
    indices = np.clip(np.searchsorted(paint, times - latency, side="right") - 1, 0, 15)
    stimuli = np.array([PALETTE[c] for c in colors], dtype=float)[indices]
    frames = np.full((len(times), 30, 40, 3), 110.0)
    spectral = np.array([1, 0.92, 0.85])
    frames[:, 5:26, 7:34] += response * (stimuli[:, None, None, :] - 145) * spectral
    frames += rng.normal(0, 1.2, frames.shape)
    frames += (times / times[-1])[:, None, None, None] * np.array([drift, -drift, 0])
    return np.clip(frames, 0, 255).astype(np.uint8), times, paint, challenge


@pytest.fixture
def signal():
    return synthetic_capture()
