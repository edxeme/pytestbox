"""A tiny green suite bundled for smoke tests and first runs."""


def test_arithmetic():
    assert 1 + 1 == 2


def test_strings():
    assert "pytestbox".upper() == "PYTESTBOX"
