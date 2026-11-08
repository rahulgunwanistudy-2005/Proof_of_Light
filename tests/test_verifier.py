import numpy as np
import pytest
from conftest import synthetic_capture
from pol_verifier.engine import chance_probability, verify


@pytest.mark.parametrize("latency", [0, 120, 300, 490])
def test_matching_sequence_with_latency_noise_and_drift(latency):
    report = verify(*synthetic_capture(latency=latency, drift=3))
    assert report["matches"] == 10
    assert report["verdict"] == "VERIFIED"
    assert abs(report["latency_ms"] - latency) <= 35
    assert report["money_movement_allowed"] is False


def test_different_body_is_not_a_valid_replay():
    report = verify(*synthetic_capture(replay=True))
    assert report["verdict"] == "FAILED"
    assert report["matches"] <= 4


def test_weak_response_is_inconclusive():
    report = verify(*synthetic_capture(response=0))
    assert report["verdict"] == "INCONCLUSIVE"


def test_duplicate_static_frames_fail_integrity(signal):
    frames, times, paint, challenge = signal
    frames[:] = frames[0]
    report = verify(frames, times, paint, challenge)
    assert report["verdict"] == "FAILED"
    assert report["integrity"]["duplicate_fraction"] == 1


def test_backwards_timestamps_fail(signal):
    frames, times, paint, challenge = signal
    times[50] = times[49]
    assert verify(frames, times, paint, challenge)["verdict"] == "FAILED"


def test_missing_secret_slot_is_not_verified(signal):
    frames, times, paint, challenge = signal
    # End during the final slot, including too little stable interior to decode it.
    mask = times < paint[-2] + 125
    report = verify(frames[mask], times[mask], paint, challenge)
    assert report["verdict"] == "INCONCLUSIVE"
    assert None in report["decoded"]


def test_fast_or_interrupted_paint_log_fails(signal):
    frames, times, paint, challenge = signal
    paint[5] = paint[4] + 20
    assert verify(frames, times, paint, challenge)["verdict"] == "FAILED"


def test_chance_null_requires_all_ten():
    assert chance_probability(10) == pytest.approx(1 / 4**10)
    assert chance_probability(9) > 1e-6
    assert chance_probability(8) > 1e-6


def test_a_reflective_print_is_not_distinguished_by_this_signal(signal):
    # A two-dimensional surface with the same time-varying reflectance gives the
    # same input to this verifier. This guards against an authenticity claim.
    report = verify(*signal)
    assert report["verdict"] == "VERIFIED"
    assert any("printed photo" in text for text in report["limitations"])
    assert report["order_bound"] is False


def test_nonfinite_input_is_rejected(signal):
    frames, times, paint, challenge = signal
    times[2] = np.nan
    with pytest.raises(ValueError, match="finite"):
        verify(frames, times, paint, challenge)


def test_missing_calibration_is_failed_not_a_nan_report(signal):
    frames, times, paint, challenge = signal
    mask = times > 3200
    report = verify(frames[mask], times[mask], paint, challenge)
    assert report["verdict"] == "FAILED"
    assert any("calibration" in text for text in report["integrity"]["errors"])
