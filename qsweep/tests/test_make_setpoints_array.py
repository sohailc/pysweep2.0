import pytest
import numpy as np
from hypothesis import given, strategies as st, assume
import logging
import re

from qsweep.convenience import make_setpoints_array

@given(
    start_value=st.floats(min_value=-5, max_value=5),
    stop_value=st.floats(min_value=-5, max_value=5),
    step_count=st.integers(min_value=0, max_value=10)
)
def test_sanity(start_value, stop_value, step_count):
    array = make_setpoints_array(
        start=start_value,
        stop=stop_value,
        step_count=step_count
    )

    assert np.allclose(
        array,
        np.linspace(
            start_value,
            stop_value,
            step_count
        )
    )


def test_inputs():

    with pytest.raises(
        ValueError,
        match="We need both start and stop"
    ):
        make_setpoints_array(
            start=0,
            stop=1,
        )

    with pytest.raises(
        ValueError,
        match="Either step or step_count need"
    ):
        make_setpoints_array(
            start=0,
            stop=1,
            step_size=0.1,
            step_count=10
        )


@st.composite
def start_stop_step_values(draw):
    start = draw(st.floats(min_value=-5, max_value=5))
    stop = draw(st.floats(min_value=-5, max_value=5))
    step = draw(st.integers(min_value=2, max_value=10))

    assume(abs(start - stop) > 0.1)
    return start, stop, step


@given(
    args=start_stop_step_values()
)
def test_step_size(args):
    start_value, stop_value, step_count = args
    step_size = (stop_value - start_value) / (step_count - 1)

    array = make_setpoints_array(
        start=start_value,
        stop=stop_value,
        step_size=step_size
    )

    actual_step_size = np.mean(np.diff(array))
    assert np.isclose(step_size, actual_step_size)


def test_steps_warning(caplog):

    start_value = 0
    stop_value = 1
    step_value = 1 / 23.542
    actual_step_value = 1 / np.round(1 / step_value)

    expected_message = f"Cannot set integer number of steps between " \
                       f"{start_value} and {stop_value} with {step_value} " \
                       f"step sizes. Changing the step size from " \
                       f"{step_value} to (.*)"

    with caplog.at_level(logging.INFO):
        make_setpoints_array(
            start=start_value,
            stop=stop_value,
            step_size=step_value
        )

        messages = [record.message for record in caplog.records]
        match = re.match(expected_message, messages[0])
        assert np.isclose(float(match[1]), actual_step_value)
