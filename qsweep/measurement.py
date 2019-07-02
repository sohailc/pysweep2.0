from qcodes.dataset.measurements import Measurement
from qsweep.base import BaseSweepObject


class SweepMeasurement(Measurement):
    def register_sweep(self, sweep_object: BaseSweepObject) -> None:

        sweep_object.parameter_table.resolve_dependencies()
        param_specs = sweep_object.parameter_table.param_specs

        # We sort by the length of `depends_on_` of ParamSpec so that
        # standalone parameters are registered first

        param_specs_sorted = sorted(
            param_specs,
            key=lambda p: len(p.depends_on_)
        )

        for param_spec in param_specs_sorted:
            self.register_custom_parameter(
                name=param_spec.name,
                label=param_spec.label,
                unit=param_spec.unit,
                basis=param_spec.inferred_from_,
                setpoints=param_spec.depends_on_,
                paramtype=param_spec.type
            )
