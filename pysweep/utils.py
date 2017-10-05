import time


def sleep(t):
    def inner(station, namespace):
        time.sleep(t)
        return {}
    return inner
