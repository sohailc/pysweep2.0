import os
import numpy as np

from pysweep.output_formatter import BaseFormatter
from pysweep.utils import DictMerge

import qcodes
import qcodes.data.location


class _SpyviewMetaWriter:
    def __init__(self, independent_params, output_file_path):
        self._independent_params = independent_params

        dirname, filename = os.path.split(output_file_path)
        meta_file_name = filename.replace(".dat", ".meta.txt")
        self._output_meta_file_path = os.path.join(dirname, meta_file_name)

        # Collect the axis values of the independent parameters
        self._axis_values = {p: [] for p in independent_params}
        self._perform_update = False

    def add(self, dictionary):
        for p in self._independent_params:
            v = dictionary[p]["value"]

            if v not in self._axis_values[p]:
                self._axis_values[p].append(v)
                self._perform_update = True

    def update_meta_file(self):

        if not self._perform_update:
            return
        self._perform_update = False

        with open(self._output_meta_file_path, "w") as fh:

            prop_funcs = [len, min, max]

            for count, p in enumerate(self._independent_params):
                axis_values = self._axis_values[p]
                props = [str(f(axis_values)) for f in prop_funcs]
                props.append(p)
                fh.write("\n".join(props) + "\n")
                prop_funcs = [len, max, min]  # I hate people to!

            if len(self._independent_params) == 2:
                props = ["1", "0", "1", "none"]
                fh.write("\n".join(props) + "\n")


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

    def __init__(self, independent_parameters=None, output_file_path=None, max_buffer_size=1000):
        """
        Parameters
        ----------
        independent_parameters: list, string, optional
            By default, the independent parameters are found by the appropriate keyword in the measurement results.
            However, in some cases we might want to specify this explicitly: 1) When the order of the parameters
            in the spyview file needs to be different then in the measurement output or 2) when the parameter is
            not included in every iteration of the measurement. The latter happens when the measurement results are
            delayed because these are read in one go from an instrument buffer.

        output_file_path: string, optional
            The default file path is "<user home>/data/<date>/<data>_<count>.dat"
        max_buffer_size: int
            We to not want to open a file handle for every iteration.
        """

        self.output_file_path = output_file_path or SpyviewFormatter.default_file_path()
        self._max_buffer_size = max_buffer_size

        self._buffer = dict()
        self._buffer_size_counter = 0
        self._started = False

        # The following attributes are determined once we begin adding dictionaries (the method "_begin" will be called)
        self._independent_params = independent_parameters
        self._inner_sweep_start_value = None
        self._meta_writer = None
        self._merger = DictMerge(unit="replace", value="append", independent_parameter="replace")

    def _write_buffer(self):

        # We will first write the independent parameters in the right order
        buffer_values = [self._buffer[param]["value"] for param in self._independent_params]

        # The rest of the variables
        buffer_values.extend([self._buffer[param]["value"] for param in self._buffer.keys() if param not
                              in self._independent_params])

        lines = ["\t".join([str(ii) for ii in i]) for i in zip(*buffer_values)]

        inner_sweep_values = np.array(buffer_values[0])

        if self._inner_sweep_start_value is None:
            self._inner_sweep_start_value = inner_sweep_values[0]

        block_indices = inner_sweep_values == self._inner_sweep_start_value
        escapes = [{True: "\n\n", False: "\n"}[i] for i in block_indices]

        lines = ["{}{}".format(*i) for i in zip(escapes, lines)]

        with open(self.output_file_path, "a") as fh:
            fh.write("".join(lines))

        self._buffer = dict()
        self._buffer_size_counter = 0

    def _begin(self, dictionary):

        self._independent_params = self._independent_params or [k for k in dictionary if "independent_parameter" in
                                                                dictionary[k]]

        self._param_x = self._independent_params[0]
        self._meta_writer = _SpyviewMetaWriter(self._independent_params, self.output_file_path)

    def add(self, dictionary):

        if not self._started:
            self._begin(dictionary)
            self._started = True

        self._meta_writer.add(dictionary)

        self._buffer = self._merger.merge([dictionary, self._buffer])
        self._buffer_size_counter += 1

        has_delayed_values = False
        for param in self._independent_params:
            if param not in self._buffer:
                has_delayed_values = True

        if has_delayed_values or self._buffer_size_counter < self._max_buffer_size:
            return

        self._write_buffer()
        self._meta_writer.update_meta_file()

    def output(self):
        return self.output_file_path

    def finalize(self):
        if self._buffer_size_counter > 1:
            self._write_buffer()
