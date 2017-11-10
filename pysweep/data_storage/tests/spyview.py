import os

from pysweep.data_storage.spyview import SpyviewStorage


def test():
    cwd = os.getcwd()
    spyview_file = os.path.join(cwd, "temp.dat")
    storage = SpyviewStorage(output_file_path=spyview_file)

    n, m = 5, 5

    x = m * list(range(n))
    y = [i//m for i in range(m * n)]
    z = [ix**2 + iy for ix, iy in zip(x, y)]

    x_dicts = [{"x": {"unit": "u", "value": v, "independent_parameter": True}} for v in x]
    y_dicts = [{"y": {"unit": "u", "value": v, "independent_parameter": True}} for v in y]
    z_dicts = [{"z": {"unit": "u", "value": v}} for v in z]

    for dict_list in zip(x_dicts, y_dicts, z_dicts):

        merge = {}
        for d in dict_list:
            merge.update(d)

        storage.add(merge)

    storage.finalize()

    with open(spyview_file, "r") as fh:
        lines = fh.readlines()

    lines = (l for l in lines)

    for iy in range(m):
        if iy > 0:
            assert next(lines) == "\n"

        for ix in range(n):

            iz = ix**2 + iy
            test_line = "\t".join(map(str, [ix, iy, iz])) + "\n"
            assert next(lines) == test_line


