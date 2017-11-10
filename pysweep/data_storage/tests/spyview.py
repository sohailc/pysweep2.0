from pysweep.data_storage.spyview import SpyviewStorage


def test():
    storage = SpyviewStorage(debug=True)

    n, m = 6, 5

    x = m * list(range(n))
    y = [i//m for i in range(m * n)]
    z = [ix**2 + iy for ix, iy in zip(x, y)]

    x_dicts = [{"x": {"unit": "u", "value": v, "independent_parameter": True}} for v in x]
    y_dicts = [{"y": {"unit": "v", "value": v, "independent_parameter": True}} for v in y]
    z_dicts = [{"z": {"unit": "w", "value": v}} for v in z]

    for dict_list in zip(x_dicts, y_dicts, z_dicts):

        merge = {}
        for d in dict_list:
            merge.update(d)

        storage.add(merge)

    storage.finalize()
    debug_out, meta_debug_out = storage.get_debug_output()

    lines = debug_out.read().decode().split("\n")
    lines = (l for l in lines)

    for iy in range(n):
        if iy > 0:
            assert next(lines) == ""

        for ix in range(m):

            iz = ix**2 + iy
            test_line = "\t".join(map(str, [ix, iy, iz]))
            assert next(lines) == test_line

    meta_debug_lines = meta_debug_out.read().decode().split("\n")
    compare = [str(i) for i in [m, min(x), max(x), "x", n, max(y), min(y), "y", 1, 0, 1, "none"]]

    assert meta_debug_lines == compare


