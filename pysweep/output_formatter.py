from pysweep.utils import DictMerge


class BaseFormatter:
    def add(self, dictionary):
        raise NotImplementedError("Please subclass")

    def output(self, *args):
        raise NotImplementedError("Please subclass")

    def finalize(self):
        raise NotImplementedError("Please subclass")


class DictFormatter(BaseFormatter, DictMerge):
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
        pass  # This is not needed in the dictionary formatter class
