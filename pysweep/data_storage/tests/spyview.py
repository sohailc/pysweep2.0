import tempfile
from pysweep.data_storage.spyview import SpyviewWriter, SpyviewMetaWriter


def test():

    output_file = tempfile.TemporaryFile()
    meta_output_file = tempfile.TemporaryFile(mode="rb+")

    def output_write_function(output):
        output_file.seek(0)
        output_file.write(output.encode())

    def meta_write_function(output):
        meta_output_file.seek(0)
        meta_output_file.write(output.encode())

    meta_writer = SpyviewMetaWriter(meta_write_function)
    writer = SpyviewWriter(output_write_function, meta_writer, max_buffer_size=10)

    n, m = 6, 5

    x = m * list(range(n))
    y = [i//n for i in range(m * n)]
    z = [ix**2 + iy for ix, iy in zip(x, y)]

    x_dicts = [{"x": {"unit": "u", "value": v, "independent_parameter": True}} for v in x]
    y_dicts = [{"y": {"unit": "v", "value": v, "independent_parameter": True}} for v in y]
    z_dicts = [{"z": {"unit": "w", "value": v}} for v in z]

    for dict_list in zip(x_dicts, y_dicts, z_dicts):

        merge = {}
        for d in dict_list:
            merge.update(d)

        writer.add(merge)

    writer.finalize()
    output_file.seek(0)

    lines = output_file.read().decode().split("\n")
    lines = (l for l in lines)

    for iy in range(m):
        if iy > 0:
            assert next(lines) == ""

        for ix in range(n):
            iz = ix**2 + iy
            test_line = "\t".join(map(str, [ix, iy, iz]))
            assert next(lines) == test_line

    meta_output_file.seek(0)
    meta_debug_lines = meta_output_file.read().decode().split("\n")
    compare = [str(i) for i in [n, min(x), max(x), "x", m, max(y), min(y), "y", 1, 0, 1, "none"]]

    assert meta_debug_lines == compare


def test_delayed():

    output_file = tempfile.TemporaryFile()
    meta_output_file = tempfile.TemporaryFile(mode="rb+")

    def output_write_function(output):
        output_file.write(output.encode())

    def meta_write_function(output):
        meta_output_file.seek(0)
        meta_output_file.write(output.encode())

    meta_writer = SpyviewMetaWriter(meta_write_function)
    writer = SpyviewWriter(output_write_function, meta_writer, max_buffer_size=10, delayed_parameters="y")

    n, m = 6, 5

    x = m * list(range(n))
    y = [i//n for i in range(m * n)]
    z = [ix**2 + iy for ix, iy in zip(x, y)]

    x_dicts = [{"x": {"unit": "u", "value": v, "independent_parameter": True}} for v in x]
    z_dicts = [{"z": {"unit": "w", "value": v}} for v in z]

    for dict_list in zip(x_dicts, z_dicts):

        merge = {}
        for d in dict_list:
            merge.update(d)

        writer.add(merge)

    y_dicts = {"y": {"unit": "v", "value": y, "independent_parameter": True}}
    writer.add(y_dicts)

    writer.finalize()
    output_file.seek(0)

    lines = output_file.read().decode().split("\n")
    lines = (l for l in lines)

    for iy in range(m):
        if iy > 0:
            assert next(lines) == ""

        for ix in range(n):
            iz = ix**2 + iy
            test_line = "\t".join(map(str, [ix, iy, iz]))
            assert next(lines) == test_line

    meta_output_file.seek(0)
    meta_debug_lines = meta_output_file.read().decode().split("\n")
    compare = [str(i) for i in [n, min(x), max(x), "x", m, max(y), min(y), "y", 1, 0, 1, "none"]]

    assert meta_debug_lines == compare