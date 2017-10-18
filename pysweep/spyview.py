import os

import qcodes
import qcodes.data.location
from pysweep.output_formatter import BaseFormatter


class _SpyviewMetaWriter:
    def __init__(self, independent_params, output_file_path):
        self._independent_params = independent_params

        dirname, filename = os.path.split(output_file_path)
        meta_file_name = filename.replace(".dat", ".meta.txt")
        self._output_meta_file_path = os.path.join(dirname, meta_file_name)

        # Collect the axis values of the independent parameters
        self._axis_values = {p: [] for p in independent_params}

    def add(self, dictionary):

        perform_update = False
        for p in self._independent_params:
            v = dictionary[p]["value"]

            if v not in self._axis_values[p]:
                self._axis_values[p].append(v)
                perform_update = True

        if perform_update:
            self._update_meta_file()

    def _update_meta_file(self):

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

    def __init__(self, output_file_path=None, buffer_size=100):

        self.output_file_path = output_file_path or SpyviewFormatter.default_file_path()
        self._buffer_size = buffer_size

        self._buffer = []
        self._started = False

        # The following attributes are determined once we begin adding dictionaries (the method "_begin" will be called)
        self._independent_params = None
        self._param_x = None  # This represents the parameter which sweeps fastest (that is the inner most sweep).
        self._start_value_param_x = None
        self._meta_writer = None

    def _write(self, string, force=False):
        self._buffer.append(string)

        if len(self._buffer) == self._buffer_size or force:
            with open(self.output_file_path, "a") as fh:
                fh.write("\n".join(self._buffer) + "\n")

            self._buffer = []

    def _begin(self, dictionary):

        self._independent_params = [k for k in dictionary if "independent_parameter" in dictionary[k]]
        self._param_x = self._independent_params[0]
        self._start_value_param_x = dictionary[self._param_x]["value"]
        self._meta_writer = _SpyviewMetaWriter(self._independent_params, self.output_file_path)

    def add(self, dictionary):

        if not self._started:
            self._begin(dictionary)

        value_param_x = dictionary[self._param_x]["value"]

        if self._start_value_param_x == value_param_x and self._started:
            self._write("\n")

        self._started = True

        params = list(self._independent_params)
        params.extend([k for k in dictionary.keys() if k not in self._independent_params])

        values_string = "\t".join([str(dictionary[p]["value"]) for p in params])
        self._write(values_string)
        self._meta_writer.add(dictionary)

    def output(self):
        return self.output_file_path

    def finalize(self):
        self._write("", force=True)
