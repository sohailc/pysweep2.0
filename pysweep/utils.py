import time


def pysleep(t):
    def inner(station, namespace):
        time.sleep(t)
        return {}
    return inner
