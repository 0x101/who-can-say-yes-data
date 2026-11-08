import pytest

from approval_relay.stats import fisher_two_sided, sign_test, wilson


def test_fisher_known_values():
    assert fisher_two_sided(12, 0, 6, 6) == pytest.approx(.013729977086447614)
    assert fisher_two_sided(12, 0, 1, 11) == pytest.approx(9.61482991e-06)
    assert fisher_two_sided(5, 5, 5, 5) == 1


def test_sign_test():
    assert sign_test(0, 0) == 1
    assert sign_test(18, 0) == pytest.approx(2 / 2 ** 18)


def test_wilson_handles_zero_denominator():
    low, high = wilson(0, 0)
    assert low != low
    assert high != high
