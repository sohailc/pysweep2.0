class Factory(dict):
    def __init__(self, func):
        super().__init__()
        self._factory = func

    def __missing__(self, name):
        return self._factory(name)
