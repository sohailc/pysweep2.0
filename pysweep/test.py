from pysweep.sweep_object import sweep_object, sweep_product
from pysweep import Namespace
import qcodes


def setter1(v):
    print("setting param1")


def setter2(v):
    print("setting param2")


def setter3(v):
    print("setting param3")


def measure(station, namespace):
    print("measuring something")
    return {"frequency": {"unit": "Hz", "value": 1E6}}


def after_end(station, namespace):
    print("doing something after finishing the sweep")
    return {}

param1 = qcodes.StandardParameter("param1", set_cmd=setter1, units="V")
param2 = qcodes.StandardParameter("param2", set_cmd=setter2, units="V")
param3 = qcodes.StandardParameter("param3", set_cmd=setter3, units="V")


def test1():
    for i in sweep_product([
        sweep_object(param1, [1, 2]),
        sweep_object(param2, [1, 2]),
        sweep_object(param3, [1, 2])
    ]).before_each(measure):
        print(i)


def test2():
    for i in sweep_product([
        sweep_object(param1, [1, 2]),
        sweep_object(param2, [1, 2]).before_each(measure),
        sweep_object(param3, [1, 2])
    ]):
        print(i)


def test3():
    for i in sweep_product([
        sweep_object(param1, [1, 2]),
        sweep_object(param2, [1, 2]),
        sweep_object(param3, [1, 2])
    ]).after_end(after_end):
        print(i)

if __name__ == "__main__":
    test3()
