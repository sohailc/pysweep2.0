import pytest
import numpy as np
from hypothesis import given, strategies as st

from qsweep.convenience import make_setpoints_array


@given(
    start_value=st.floats(min_value=-5, max_value=5),
    stop_value=st.floats(min_value=-5, max_value=5),
    step_count=st.integers(min_value=0, max_value=10)
)
def test_sanity(start_value, stop_value, step_count):
    array = make_setpoints_array(
        start_value=start_value,
        stop_value=stop_value,
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
            start_value=0,
            stop_value=1,
        )

    with pytest.raises(
        ValueError,
        match="Either step or step_count need"
    ):
        make_setpoints_array(
            start_value=0,
            stop_value=1,
            step_value=0.1,
            step_count=10
        )

@given(
    start_value=st.floats(min_value=-5, max_value=5),
    stop_value=st.floats(min_value=-5, max_value=5),
    step_count=st.integers(min_value=0, max_value=10)
)
def test_step_size(start_value, stop_value, step_count):

    step_size = (stop_value - start_value) / step_count

    array = make_setpoints_array(
        start_value=start_value,
        stop_value=stop_value,
        step_value=step_size
    )

    actual_step_size = np.mean(np.diff(array))
    assert np.isclose(step_size, actual_step_size)


def test_steps_warning():

    make_setpoints_array(
        start_value=0,
        stop_value=1,
        step_value=1/2.5
    )
