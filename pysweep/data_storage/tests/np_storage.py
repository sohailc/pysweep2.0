import numpy as np

from pysweep.data_storage import NpStorage
from pysweep import sweep


def test_1d():

    param = lambda s, n, v: {"x": {"unit": "", "value": v, "independent_parameter": True}}
    measure_values = np.linspace(-1, 1, 4)
    g = (i for i in measure_values)
    measure = lambda s, n: {"m": {"unit": "", "value": next(g)}}

    coordinate_values = np.array([0, 1, 2, 3])
    so = sweep(param, coordinate_values)(measure)

    store = NpStorage()

    for i in so:
        store.add(i)

    assert np.all(store["m"]["m []"].flatten() == measure_values)
    assert np.all(store["m"]["x []"].flatten() == coordinate_values)


def test_2d():

    m, n = 5, 7

    param_x = lambda s, n, v: {"x": {"unit": "", "value": v, "independent_parameter": True}}
    coordinate_values_x = np.arange(m)

    param_y = lambda s, n, v: {"y": {"unit": "", "value": v, "independent_parameter": True}}
    coordinate_values_y = np.arange(n)

    measure_values = np.linspace(-1, 1, m * n)
    g = (i for i in measure_values)
    measure = lambda s, n: {"m": {"unit": "", "value": next(g)}}

    so = sweep(param_x, coordinate_values_x)(sweep(param_y, coordinate_values_y)(measure))

    store = NpStorage()

    for i in so:
        store.add(i)

    assert np.all(store["m"]["m []"].flatten() == measure_values)

    tmpx = store["m"]["x []"].reshape((m, n))
    tmpy = store["m"]["y []"].reshape((m, n))
    assert np.all(np.vstack([tmpy, tmpx]) == np.vstack(np.meshgrid(coordinate_values_y, coordinate_values_x)))


def test_2d_nd_measurement():
    m, n, o = 5, 7, 3

    param_x = lambda s, n, v: {"x": {"unit": "", "value": v, "independent_parameter": True}}
    coordinate_values_x = np.arange(m)

    param_y = lambda s, n, v: {"y": {"unit": "", "value": v, "independent_parameter": True}}
    coordinate_values_y = np.arange(n)

    measure_values = np.arange(m * n * o).reshape((m * n, o))
    g = (i for i in measure_values)
    measure = lambda s, n: {"m": {"unit": "", "value": next(g)}}

    so = sweep(param_x, coordinate_values_x)(sweep(param_y, coordinate_values_y)(measure))

    store = NpStorage()

    for i in so:
        store.add(i)

    assert np.all(store["m"]["m []"] == measure_values)

    tmpx = store["m"]["x []"].reshape((m, n))
    tmpy = store["m"]["y []"].reshape((m, n))
    assert np.all(np.vstack([tmpy, tmpx]) == np.vstack(np.meshgrid(coordinate_values_y, coordinate_values_x)))