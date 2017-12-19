import numpy as np

from pysweep.data_storage.np_storage import NpStorage


class SpyviewStorage(NpStorage):

    def __init__(self, store_parameters):
        super().__init__()
        self._store_parameters = store_parameters

    def add(self, record):
        super().add(record)
        for param in self._store_parameters:
            page = self.output(param)
            self.write_page(page)

    @staticmethod
    def insert_field(array, position, field_name, field_dtype):

        names = array.dtype.names

        new_dtype = [array.dtype[n] for n in names]
        new_dtype.insert(position, field_dtype)

        new_names = list(names)
        new_names.insert(position, field_name)

        new_array = np.zeros(array.shape, dtype=list(zip(new_names, new_dtype)))

        for name in names:
            new_array[name] = array[name]

        return new_array

    def write_page(self, page):
        params = page.dtype.names
        if len(params) == 2:
            page = self.insert_field(page, 1, "empty", np.dtype((int, (1,))))

        inner = params[0]
        inner_sweep_values = page[inner]
        block_indices = inner_sweep_values == inner_sweep_values[0]

        escapes = [{True: "\n\n", False: "\n"}[i] for i in block_indices]
        escapes[0] = ""

        lines = ["\t".join([str(i[0]) for i in p[0]]) for p in list(zip(page))]
        lines = ["{}{}".format(*i) for i in zip(escapes, lines)]
        out = "".join(lines)





