import numpy as np
from model.calibrate import IsotonicCalibrator


def test_isotonic_is_monotonic_and_corrects_overconfidence():
    rng = np.random.default_rng(0)
    prob = np.linspace(0.1, 0.9, 400)
    # Model is overconfident: true hit rate is only half the predicted probability.
    hit = (rng.random(400) < prob / 2).astype(float)
    cal = IsotonicCalibrator().fit(prob, hit)
    out = cal.transform(np.array([0.2, 0.5, 0.8]))
    assert out[0] <= out[1] + 1e-9 <= out[2] + 1e-9   # non-decreasing
    assert out[2] < 0.8                                # corrected downward


def test_transform_before_fit_raises():
    try:
        IsotonicCalibrator().transform([0.5])
        assert False, "expected RuntimeError"
    except RuntimeError:
        pass
