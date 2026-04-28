import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl


class FuzzyController:
    def __init__(
        self,
        input_range,
        output_range,
        input_sets=None,
        output_sets=None,
        rules=None,
        step=0.01
    ):
        self.error = ctrl.Antecedent(
            np.arange(-input_range, input_range + step, step),
            'error'
        )

        self.output = ctrl.Consequent(
            np.arange(-output_range, output_range + step, step),
            'output'
        )

        self.input_range = input_range
        self.output_range = output_range

        # 如果外部沒有定義，就使用預設模糊集合
        if input_sets is None:
            input_sets = {
                'negative': ('trimf', [-input_range, -input_range / 2, 0]),
                'zero': ('trimf', [-input_range / 2, 0, input_range / 2]),
                'positive': ('trimf', [0, input_range / 2, input_range])
            }

        if output_sets is None:
            output_sets = {
                'negative': ('trimf', [-output_range, -output_range / 2, 0]),
                'zero': ('trimf', [-output_range / 2, 0, output_range / 2]),
                'positive': ('trimf', [0, output_range / 2, output_range])
            }

        self._build_membership_functions(self.error, input_sets)
        self._build_membership_functions(self.output, output_sets)

        # 如果外部沒有定義規則，就使用預設規則
        if rules is None:
            rules = [
                ('negative', 'negative'),
                ('zero', 'zero'),
                ('positive', 'positive')
            ]

        rule_objects = self._build_rules(rules)

        self.control_system = ctrl.ControlSystem(rule_objects)
        self.simulation = ctrl.ControlSystemSimulation(self.control_system)

    def _build_membership_functions(self, variable, sets):
        """
        sets 格式：
        {
            'negative': ('trimf', [-10, -5, 0]),
            'zero': ('trimf', [-5, 0, 5]),
            'positive': ('trimf', [0, 5, 10])
        }
        """

        for name, config in sets.items():
            mf_type, params = config

            if mf_type == 'trimf':
                variable[name] = fuzz.trimf(variable.universe, params)

            elif mf_type == 'trapmf':
                variable[name] = fuzz.trapmf(variable.universe, params)

            elif mf_type == 'gaussmf':
                mean, sigma = params
                variable[name] = fuzz.gaussmf(variable.universe, mean, sigma)

            else:
                raise ValueError(f"Unsupported membership function type: {mf_type}")

    def _build_rules(self, rules):
        """
        rules 格式：
        [
            ('negative', 'negative'),
            ('zero', 'zero'),
            ('positive', 'positive')
        ]

        表示：
        IF error is negative THEN output is negative
        """

        rule_objects = []

        for input_label, output_label in rules:
            rule = ctrl.Rule(
                self.error[input_label],
                self.output[output_label]
            )
            rule_objects.append(rule)

        return rule_objects

    def reset(self):
        self.simulation.reset()

    def update(self, error, dt=None):
        self.simulation.input['error'] = error
        self.simulation.compute()
        return self.simulation.output['output']

if __name__ == "__main__":

    input_sets = {
        'NB': ('trimf', [-10, -10, -5]),
        'NS': ('trimf', [-10, -5, 0]),
        'ZO': ('trimf', [-2, 0, 2]),
        'PS': ('trimf', [0, 5, 10]),
        'PB': ('trimf', [5, 10, 10])
    }

    output_sets = {
        'NB': ('trimf', [-1, -1, -0.5]),
        'NS': ('trimf', [-1, -0.5, 0]),
        'ZO': ('trimf', [-0.2, 0, 0.2]),
        'PS': ('trimf', [0, 0.5, 1]),
        'PB': ('trimf', [0.5, 1, 1])
    }

    rules = [
        ('NB', 'NB'),
        ('NS', 'NS'),
        ('ZO', 'ZO'),
        ('PS', 'PS'),
        ('PB', 'PB')
    ]

    controller = FuzzyController(
        input_range=10,
        output_range=1,
        input_sets=input_sets,
        output_sets=output_sets,
        rules=rules
    )

    output = controller.update(error=3.5)
    print(output)