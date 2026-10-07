"""Tests for pytest summary parsing."""

from pytestbox.parser import parse_summary


def test_green_suite_quiet_output():
    output = ".\n1 passed in 0.02s\n"
    assert parse_summary(output) == {"passed": 1}


def test_mixed_counts_without_q_flag():
    output = "collected 3 items\ntest_x.py F..\n========= 1 failed, 2 passed in 0.03s =========\n"
    assert parse_summary(output) == {"failed": 1, "passed": 2}


def test_summary_without_duration():
    assert parse_summary("1 failed, 2 passed") == {"failed": 1, "passed": 2}


def test_singular_warning_key():
    assert parse_summary("1 passed, 1 warning in 0.05s") == {
        "passed": 1,
        "warning": 1,
    }


def test_no_tests_ran_is_not_a_count():
    assert parse_summary("no tests ran in 0.01s") is None


def test_crash_output_has_no_summary():
    assert parse_summary("Traceback (most recent call last):\n  boom") is None


def test_empty_output():
    assert parse_summary("") is None


def test_summary_hidden_in_captured_prints_does_not_win():
    # a test that prints a fake summary line, then the real one last
    output = "fake print: 99 passed in 9.99s\n2 passed in 0.01s\n"
    assert parse_summary(output) == {"passed": 2}


def test_errors_key_is_recognized():
    assert parse_summary("2 errors in 0.10s") == {"errors": 2}
