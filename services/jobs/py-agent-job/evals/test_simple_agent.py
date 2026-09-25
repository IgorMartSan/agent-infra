import pytest

from evals.support import evaluate_case, load_cases


@pytest.mark.parametrize("case", load_cases("simple-agent"), ids=lambda case: case["id"])
def test_reference_answer(case):
    evaluate_case("simple-agent", case)
