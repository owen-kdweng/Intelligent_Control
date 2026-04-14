# pip install numpy==2.4.4 networkx==3.6.1 scipy==1.17.1 scikit-fuzzy==0.5.0

import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl

# 定義輸入與輸出變數
temperature = ctrl.Antecedent(np.arange(0, 41, 1), 'temperature')   # 0~40 度
fan_speed = ctrl.Consequent(np.arange(0, 101, 1), 'fan_speed')      # 0~100 %

# 定義輸入元素模糊集合
temperature['low'] = fuzz.trimf(temperature.universe, [0, 0, 20])
temperature['medium'] = fuzz.trimf(temperature.universe, [10, 20, 30])
temperature['high'] = fuzz.trimf(temperature.universe, [20, 40, 40])

# 定義輸出元素模糊集合
fan_speed['low'] = fuzz.trimf(fan_speed.universe, [0, 0, 50])
fan_speed['medium'] = fuzz.trimf(fan_speed.universe, [25, 50, 75])
fan_speed['high'] = fuzz.trimf(fan_speed.universe, [50, 100, 100])

# 建立規則庫
rule1 = ctrl.Rule(temperature['low'], fan_speed['low'])
rule2 = ctrl.Rule(temperature['medium'], fan_speed['medium'])
rule3 = ctrl.Rule(temperature['high'], fan_speed['high'])

# 建立控制系統
fan_ctrl = ctrl.ControlSystem([rule1, rule2, rule3])
fan_sim = ctrl.ControlSystemSimulation(fan_ctrl)

# 輸入數值並推論
fan_sim.input['temperature'] = 15
fan_sim.compute()

# 顯示結果
print(f"溫度 = 15°C")
print(f"風扇輸出 = {fan_sim.output['fan_speed']:.2f}%")