import matplotlib.pyplot as plt
import numpy as np


class DataPlot:
    def __init__(self, data):
        self._data = data
        self._independents = [k for k in data if "independent_parameter" in data[k]]
        self._dependents = [k for k in data if "independent_parameter" not in data[k]]

        n_dependents = len(self._dependents)
        fig, axes = plt.subplots(n_dependents)
        self._axes = np.atleast_1d(axes)

        if len(self._independents) == 2:
            self._plot_2d()
        elif len(self._independents) == 1:
            self._plot_1d()
        else:
            raise ValueError("can only plot 1d or 2d for now")

        plt.show()

    def _plot_1d(self):

        independent = self._independents[0]
        x = self._data[independent]["value"]
        x_unit = self._data[independent]["unit"]
        x_label = "{name} [{unit}]".format(name=independent, unit=x_unit)

        for count, dependent in enumerate(self._dependents):
            y = self._data[dependent]["value"]
            y_unit = self._data[dependent]["unit"]
            y_label = "{name} [{unit}]".format(name=dependent, unit=y_unit)

            ax = self._axes[count]
            ax.plot(x, y)
            ax.set_xlabel(x_label)
            ax.set_ylabel(y_label)

    def _plot_2d(self):

        x, y = [self._data[k]["value"] for k in self._independents]

        units = [self._data[k]["unit"] for k in self._independents]
        x_label, y_label = ["{name} [{unit}]".format(name=name, unit=unit) for name, unit in
                            zip(self._independents, units)]

        for count, dependent in enumerate(self._dependents):
            values = self._data[dependent]["value"]
            unit = self._data[dependent]["unit"]

            ax = self._axes[count]
            ax.scatter(x, y, c=values)
            ax.set_xlabel(x_label)
            ax.set_ylabel(y_label)
            ax.set_title("{name} [{unit}]".format(name=dependent, unit=unit))