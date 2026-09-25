import pytest

from evals.support import evaluate_case, load_cases


@pytest.mark.parametrize("case", load_cases("argus-agent"), ids=lambda case: case["id"])
def test_reference_answer(case):
    evaluate_case("argus-agent", case)
