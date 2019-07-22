import pytest

from qcodes import Parameter
# pylint: disable=unused-import
from qcodes.tests.dataset.temporary_databases import empty_temp_db, experiment

from qsweep.measurement import SweepMeasurement
from qsweep import sweep

from ._test_tools import Factory


@pytest.fixture()
def parameters():
    def create_param(name):
        return Parameter(name, set_cmd=None, get_cmd=None)

    return Factory(create_param)


@pytest.mark.usefixtures("experiment")
def test_register_sweep(parameters):

    p = parameters["p"]
    sweep_object = sweep(p, start=0, stop=1, step_size=0.1)
    measurement = SweepMeasurement()
    measurement.register_sweep(sweep_object)

    with measurement.run() as datasaver:
        for data in sweep_object:
            datasaver.add_result(*data.items())

    data = datasaver.dataset.get_data(p)
    assert data == [[i/10] for i in range(0, 11)]
