import os

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

            for count, p in enumerate(self._independent_params):

                if count == 0:
                    prop_funcs = [len, min, max]
                else:
                    prop_funcs = [len, max, min]  # I hate people to! BTW... this inconsistency is another excellent
                    # reason to ditch this "spyview" crap ASAP

                axis_values = self._axis_values[p]
                props = [str(f(axis_values)) for f in prop_funcs]
                props.append(p)
                fh.write("\n".join(props) + "\n")

            if len(self._independent_params) == 2:
                props = ["1", "0", "1", "none"]
                fh.write("\n".join(props) + "\n")


class SpyviewFormatter(BaseFormatter):
    def __init__(self, independent_params, output_file_path, buffer_size=10):

        if len(independent_params) not in [2, 3]:
            raise ValueError("The number of independent parameters needs to be either 2 or 3 for the spyview formatter")

        self._independent_params = independent_params

        # This represents the parameter which sweeps fastest (that is the inner most sweep).
        self._param_x = self._independent_params[0]

        self._start_value_param_x = None
        self.output_file_path = output_file_path

        self._buffer = []
        self._buffer_size = buffer_size
        self._meta_writer = _SpyviewMetaWriter(independent_params, output_file_path)

    def _write(self, string, force=False):
        self._buffer.append(string)

        if len(self._buffer) == self._buffer_size or force:
            with open(self.output_file_path, "a") as fh:
                fh.write("\n".join(self._buffer) + "\n")

            self._buffer = []

    def add(self, dictionary):

        value_param_x = dictionary[self._param_x]["value"]

        if self._start_value_param_x is None:
            self._start_value_param_x = value_param_x
        elif self._start_value_param_x == value_param_x:
            self._write("\n")

        params = list(self._independent_params)
        params.extend([k for k in dictionary.keys() if k not in self._independent_params])

        values_string = "\t".join([str(dictionary[p]["value"]) for p in params])
        self._write(values_string)
        self._meta_writer.add(dictionary)

    def output(self):
        return self.output_file_path

    def finalize(self):
        self._write("", force=True)
