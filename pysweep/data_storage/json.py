"""
Initial work on the JSON storage class. Note that for now we are accumulating data in a dictionary without writing
anything to file yet
"""

from pysweep.data_storage.base_storage import BaseStorage
from pysweep.utils import DictMerge


class JSONStorage(BaseStorage, DictMerge):
    def __init__(self, **strategy):
        super().__init__(**strategy)
        self.buffer = []

    def add(self, dictionary):
        self.buffer.append(dictionary)

    def output(self, name):
        d = dict()
        for ibuffer in self.buffer:
            if name in ibuffer:
                d = self.merge([ibuffer, d])
        return d

    def finalize(self):
        pass  # TODO: Left off here
