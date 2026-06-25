import math
from model.blend import blend_probs


def test_blend_w1_returns_model():
    m = {"home": 0.5, "draw": 0.3, "away": 0.2}
    mk = {"home": 0.4, "draw": 0.3, "away": 0.3}
    b = blend_probs(m, mk, 1.0)
    assert all(math.isclose(b[k], m[k]) for k in m)


def test_blend_w0_returns_market():
    m = {"home": 0.5, "draw": 0.3, "away": 0.2}
    mk = {"home": 0.4, "draw": 0.3, "away": 0.3}
    b = blend_probs(m, mk, 0.0)
    assert all(math.isclose(b[k], mk[k]) for k in mk)


def test_blend_half_sums_to_one():
    b = blend_probs({"home": 0.6, "draw": 0.3, "away": 0.1},
                    {"home": 0.4, "draw": 0.3, "away": 0.3}, 0.5)
    assert math.isclose(sum(b.values()), 1.0)


def test_blend_rejects_bad_weight():
    try:
        blend_probs({"home": 1.0}, {"home": 1.0}, 1.5)
        assert False, "expected ValueError"
    except ValueError:
        pass
