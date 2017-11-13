from hypothesis import given, settings
from hypothesis.strategies import integers

import tempfile
from pysweep.data_storage.spyview import SpyviewWriter, SpyviewMetaWriter


def read_lines(file):
    file.seek(0)
    return file.read().decode().split("\n")


@given(integers(min_value=3, max_value=700), integers(min_value=5, max_value=500))
@settings(max_examples=30)
def test_1d(m, max_buffer_size):

    output_file = tempfile.TemporaryFile()
    meta_output_file = tempfile.TemporaryFile(mode="rb+")

    def output_write_function(output):
        output_file.seek(0)
        output_file.write(output.encode())

    def meta_write_function(output):
        meta_output_file.seek(0)
        meta_output_file.write(output.encode())

    meta_writer = SpyviewMetaWriter(meta_write_function)
    writer = SpyviewWriter(output_write_function, meta_writer, max_buffer_size=max_buffer_size)

    x = list(range(m))
    y = [ix ** 2 + 3 for ix in x]

    x_dicts = [{"x": {"unit": "u", "value": v, "independent_parameter": True}} for v in x]
    y_dicts = [{"y": {"unit": "v", "value": v}} for v in y]

    write_count = 0
    for dict_list in zip(x_dicts, y_dicts):

        merge = {}
        for d in dict_list:
            merge.update(d)

        writer.add(merge)
        write_count += 1
        non_empty_line_count = len([l for l in read_lines(output_file) if l != ""])
        assert non_empty_line_count == max_buffer_size * (write_count // max_buffer_size)

    writer.finalize()

    lines = read_lines(output_file)
    lines = (l for l in lines)

    for ix in range(m):
        assert next(lines) == "\t".join(map(str, [ix, 0, ix ** 2 + 3]))

    meta_debug_lines = read_lines(meta_output_file)
    compare = [str(i) for i in [m, min(x), max(x), "x", 1, 0, 0, "empty", 1, 0, 1, "none"]]

    assert meta_debug_lines == compare


@given(integers(min_value=3, max_value=7), integers(min_value=3, max_value=7), integers(min_value=5, max_value=500))
@settings(max_examples=30)
def test(n, m, max_buffer_size):

    output_file = tempfile.TemporaryFile()
    meta_output_file = tempfile.TemporaryFile(mode="rb+")

    def output_write_function(output):
        output_file.seek(0)
        output_file.write(output.encode())

    def meta_write_function(output):
        meta_output_file.seek(0)
        meta_output_file.write(output.encode())

    meta_writer = SpyviewMetaWriter(meta_write_function)
    writer = SpyviewWriter(output_write_function, meta_writer, max_buffer_size=max_buffer_size)

    x = m * list(range(n))
    y = [i//n for i in range(m * n)]
    z = [ix**2 + iy for ix, iy in zip(x, y)]

    x_dicts = [{"x": {"unit": "u", "value": v, "independent_parameter": True}} for v in x]
    y_dicts = [{"y": {"unit": "v", "value": v, "independent_parameter": True}} for v in y]
    z_dicts = [{"z": {"unit": "w", "value": v}} for v in z]

    write_count = 0
    for dict_list in zip(x_dicts, y_dicts, z_dicts):

        merge = {}
        for d in dict_list:
            merge.update(d)

        writer.add(merge)
        write_count += 1
        non_empty_line_count = len([l for l in read_lines(output_file) if l != ""])

        assert non_empty_line_count == max_buffer_size * (write_count // max_buffer_size)

    writer.finalize()

    lines = read_lines(output_file)
    lines = (l for l in lines)

    for iy in range(m):
        if iy > 0:
            assert next(lines) == ""

        for ix in range(n):
            iz = ix**2 + iy
            test_line = "\t".join(map(str, [ix, iy, iz]))
            assert next(lines) == test_line

    meta_debug_lines = read_lines(meta_output_file)
    compare = [str(i) for i in [n, min(x), max(x), "x", m, max(y), min(y), "y", 1, 0, 1, "none"]]

    assert meta_debug_lines == compare


@given(integers(min_value=3, max_value=7), integers(min_value=3, max_value=7), integers(min_value=5, max_value=500))
@settings(max_examples=30)
def test_delayed(n, m, max_buffer_size):

    output_file = tempfile.TemporaryFile()
    meta_output_file = tempfile.TemporaryFile(mode="rb+")

    def output_write_function(output):
        output_file.seek(0)
        output_file.write(output.encode())

    def meta_write_function(output):
        meta_output_file.seek(0)
        meta_output_file.write(output.encode())

    meta_writer = SpyviewMetaWriter(meta_write_function)
    writer = SpyviewWriter(output_write_function, meta_writer, max_buffer_size=max_buffer_size, delayed_parameters="y")

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

    lines = read_lines(output_file)
    lines = (l for l in lines)

    for iy in range(m):
        if iy > 0:
            assert next(lines) == ""

        for ix in range(n):
            iz = ix**2 + iy
            test_line = "\t".join(map(str, [ix, iy, iz]))
            assert next(lines) == test_line

    meta_debug_lines = read_lines(meta_output_file)
    compare = [str(i) for i in [n, min(x), max(x), "x", m, max(y), min(y), "y", 1, 0, 1, "none"]]

    assert meta_debug_lines == compare

