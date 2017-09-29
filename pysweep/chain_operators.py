"""
This module contains functions which are able to chain point functions together.
"""


def tpl(value):
    if not isinstance(value, tuple):
        return value,
    return value


def pass_operator(point_functions):

    if len(point_functions) > 1:
        raise ValueError("Cannot use a pass operator on a list of point functions")

    def inner(station, namespace):
        for value in point_functions[0](station, namespace):
            yield tpl(value), (True,)

    return inner


def _product_two_operator(outer_pf, inner_pf):
    def mov(atuple):
        yield atuple
        while True:
            yield (False,) * len(atuple)

    def inner(station, namespace):
        for v1, j in outer_pf(station, namespace):
            m = mov(j)
            for v2 in inner_pf(station, namespace):
                yield tpl(v2) + tpl(v1), (True,) + next(m)

    return inner


def product_operator(point_functions):
    """
    Parameters
    ----------
    point_functions: list, callable
        Point functions are generator creating functions which accept station and namespace as arguments. The unrolling
        of the generator yields floating point values which which are used to set parameters

    Return
    ------
    callable:
         a generator creating callable of two arguments; station and namespace. Unrolling this generator will yield a
         tuple of length two

    Example
    -------
    >>> x = lambda station, namespace: (i for i in [0, 1, 2, 3])
    >>> y = lambda station, namespace: (i for i in [4, 5, 6, 6])
    >>> z = lambda station, namespace: (i for i in [9, 1, 6])

    >>> for xyz in product_operator([x, y, z])(None, None):
    >>> print(xyz)
    ((0, 4, 9), (True, True, True))
    ((1, 4, 9), (True, False, False))
    ((2, 4, 9), (True, False, False))
    ((3, 4, 9), (True, False, False))
    ((0, 5, 9), (True, True, False))
    ....
    """
    def add_trues(point_function):
        def adder(station, namespace):
            for v in point_function(station, namespace):
                yield v, (True,)

        return adder

    def inner(station, namespace):
        rval = add_trues(point_functions[-1])
        for pf in point_functions[-2::-1]:
            rval = _product_two_operator(rval, pf)

        return rval(station, namespace)

    return inner