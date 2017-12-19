import numpy as np
import os
import json
import time

import qcodes

from pysweep.data_storage.np_storage import NpStorage
from pysweep.data_storage.base_storage import BaseStorage


class SpyviewWriter(NpStorage):

    def __init__(self, store_parameters, writer_function, write_interval_time=5):
        super().__init__()
        self._store_parameters = store_parameters
        self._writer_function = writer_function
        self._write_interval_time = write_interval_time
        self._last_write_action = time.time()

    def add(self, record):
        super().add(record)

        current_time = time.time()
        if current_time - self._last_write_action < self._write_interval_time:
            return
        self._last_write_action = current_time
        self._write()

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

    def _write(self):
        for param in self._store_parameters:
            page = self.output(param)
            self._write_page(page)

    def _write_page(self, page):
        params = page.dtype.names
        if len(params) == 2:
            page = self.insert_field(page, 1, "empty", np.dtype((int, (1,))))

        inner = params[0]
        inner_sweep_values = page[inner]
        block_indices = (inner_sweep_values == inner_sweep_values[0]).flatten()
        escapes = [{True: "\n\n", False: "\n"}[i] for i in block_indices]
        escapes[0] = ""

        lines = ["\t".join([str(i[0]) for i in p[0]]) for p in list(zip(page))]
        lines = ["{}{}".format(*i) for i in zip(escapes, lines)]
        out = "".join(lines)
        self._writer_function(out)

    def finalize(self):
        self._write()


class SpyviewStorage(BaseStorage):
    """
    The spyview storage module
    """
    # The storage folder can be set by the user using the "set_storage_folder" interface.
    storage_folder = ""

    # If the user does not set the storage folder, use the default one
    @staticmethod
    def default_storage_folder():
        home_path = os.path.expanduser("~")
        storage_folder = os.path.join(home_path, "data")
        return storage_folder

    @classmethod
    def set_storage_folder(cls, folder: str) ->None:
        cls.storage_folder = folder

    @classmethod
    def default_file_path(cls) ->str:
        """
        The default data output path.
        """
        if cls.storage_folder is "":
            cls.storage_folder = cls.default_storage_folder()

        data_path = os.path.join(cls.storage_folder, "{date}", "{date}_{counter}.dat")
        loc_provider = qcodes.data.location.FormatLocation(fmt=data_path)
        io = qcodes.DiskIO('.')
        file_path = loc_provider(io)

        dir_name, _ = os.path.split(file_path)
        if not os.path.exists(dir_name):
            os.makedirs(dir_name, exist_ok=True)

        return file_path

    @staticmethod
    def meta_file_path(output_file_path: str):
        dirname, filename = os.path.split(output_file_path)
        meta_file_name = filename.replace(".dat", ".meta.txt")
        return os.path.join(dirname, meta_file_name)

    @staticmethod
    def snapshot_file_path(output_file_path):
        dirname, filename = os.path.split(output_file_path)
        json_file_name = filename.replace(".dat", ".station_snapshot.json")
        return os.path.join(dirname, json_file_name)

    def __init__(self, store_parameters):

        self._output_file_path = SpyviewStorage.default_file_path()
        self._output_meta_file_path = SpyviewStorage.meta_file_path(self._output_file_path)
        self._data_folder, _ = os.path.split(self._output_file_path)

        self._writer = SpyviewWriter(store_parameters, writer_function=self._writer_function)

    def _meta_writer_function(self, output):

        with open(self._output_meta_file_path, "w") as fh:
            fh.write(output)

    def _writer_function(self, output):

        with open(self._output_file_path, "w") as fh:
            fh.write(output)

    def output_files(self):
        return self._output_file_path, self._output_meta_file_path

    def add(self, dictionary):
        self._writer.add(dictionary)

    def output(self, item):
        return self._writer.output(item)

    def finalize(self):
        self._writer.finalize()

    def save_json_snapshot(self, snapshot):

        json_file = SpyviewStorage.snapshot_file_path(self._output_file_path)
        with open(json_file, 'w') as meta_file:
            json.dump(snapshot, meta_file, sort_keys=True, indent=4, ensure_ascii=False)



