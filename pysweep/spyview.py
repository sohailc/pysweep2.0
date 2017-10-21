import os
import numpy as np

from pysweep.output_formatter import BaseFormatter
from pysweep.utils import DictMerge

import qcodes
import qcodes.data.location


class SpyviewFormatter(BaseFormatter):

    @staticmethod
    def default_file_path():
        io = qcodes.DiskIO('.')
        home_path = os.path.expanduser("~")
        data_path = os.path.join(home_path, "data", "{date}", "{date}_{counter}.dat")
        loc_provider = qcodes.data.location.FormatLocation(fmt=data_path)
        file_path = loc_provider(io)

        dir_name, _ = os.path.split(file_path)
        if not os.path.exists(dir_name):
            os.makedirs(dir_name, exist_ok=True)

        return file_path

    def __init__(self, delayed_parameters=None, output_file_path=None, max_buffer_size=1000):
        self._output_file_path = output_file_path or SpyviewFormatter.default_file_path()
        self._max_buffer_size = max_buffer_size
        self._delayed_parameters = delayed_parameters or []

        self._buffer = dict()
        self._merger = DictMerge(unit="replace", value="append", independent_parameter="replace")
        self._inner_sweep_start_value = None

    def _get_buffer_size(self):
        if self._buffer == dict():
            return 0

        size = np.inf
        for p in self._buffer.values():
            value = p["value"]
            if hasattr(value, "__len__"):
                this_size = len(value)
            else:
                this_size = 1

            size = min([size, this_size])
        return size

    def _write_buffer(self):

        # We will first write the independent parameters in the right order
        independent_parameters = [k for k in self._buffer if "independent_parameter" in self._buffer[k]]
        buffer_values = [self._buffer[param]["value"] for param in independent_parameters]

        # The rest of the variables
        buffer_values.extend([self._buffer[param]["value"] for param in self._buffer.keys() if param not
                              in independent_parameters])

        inner_sweep_values = np.array(buffer_values[0])

        if self._inner_sweep_start_value is None:
            self._inner_sweep_start_value = inner_sweep_values[0]

        block_indices = inner_sweep_values == self._inner_sweep_start_value
        escapes = [{True: "\n\n", False: "\n"}[i] for i in block_indices]

        lines = ["\t".join([str(ii) for ii in i]) for i in zip(*buffer_values)]
        lines = ["{}{}".format(*i) for i in zip(escapes, lines)]

        with open(self._output_file_path, "a") as fh:
            fh.write("".join(lines))

        self._buffer = dict()

    def add(self, dictionary):
        delayed_params_buffer = {param: {"value": []} for param in self._delayed_parameters}

        self._buffer = self._merger.merge([dictionary, delayed_params_buffer, self._buffer])
        if self._get_buffer_size() >= self._max_buffer_size:
            self._write_buffer()

    def finalize(self):
        if self._get_buffer_size() >= 2:
            self._write_buffer()
