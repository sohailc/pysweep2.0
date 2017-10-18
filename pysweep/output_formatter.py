from pysweep.utils import DictMerge


class BaseFormatter:
    def add(self, dictionary):
        raise NotImplementedError("Please subclass")

    def output(self):
        raise NotImplementedError("Please subclass")

    def finalize(self):
        raise NotImplementedError("Please subclass")


class DictFormatter(BaseFormatter, DictMerge):
    def __init__(self, **strategy):
        super().__init__(**strategy)
        self.buffer = {}

    def add(self, dictionary):
        self.buffer = self.merge([dictionary, self.buffer])

    def output(self):
        return self.buffer

    def finalize(self):
        pass  # This is not needed in the dictionary formatter class
