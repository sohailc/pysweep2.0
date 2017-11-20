"""
The prototype class for data storage
"""


class BaseStorage:
    def add(self, dictionary):
        raise NotImplementedError("Please subclass")

    def output(self, *args):
        raise NotImplementedError("Please subclass")

    def finalize(self):
        raise NotImplementedError("Please subclass")

    def save_json_snapshot(self, snapshot):
        raise NotImplementedError("Please subclass")