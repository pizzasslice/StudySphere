
import pytest

from module_b import marks_to_grade


@pytest.mark.parametrize("marks, expected", [
    (95, ('O', 10.0)),
    (90, ('O', 10.0)),
    (85, ('A+', 9.0)),
    (80, ('A+', 9.0)),
    (75, ('A', 8.0)),
    (70, ('A', 8.0)),
    (65, ('B+', 7.0)),
    (60, ('B+', 7.0)),
    (55, ('B', 6.0)),
    (50, ('B', 6.0)),
    (45, ('C', 5.0)),
    (40, ('C', 5.0)),
    (39, ('F', 0.0)),
    (0, ('F', 0.0)),
])
def test_marks_to_grade(marks, expected):
    assert marks_to_grade(marks) == expected


def test_grading_scale():
    from module_b import GRADING_SCALE

    assert len(GRADING_SCALE) == 7


def test_attendance_percentage_constant():
    from module_b import MIN_ATTENDANCE_PCT

    assert MIN_ATTENDANCE_PCT == 75.0


def test_remaining_credits():
    from module_b import REMAINING_CREDITS

    assert REMAINING_CREDITS == 20
