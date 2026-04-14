# pip install matplotlib scikit-fuzzy numpy

import numpy as np
import matplotlib.pyplot as plt
import skfuzzy as fuzz
from skfuzzy import control as ctrl

# =========================
# 1. 定義輸入與輸出變數
# =========================
temperature = ctrl.Antecedent(np.arange(0, 41, 1), 'temperature')   # 0~40 度
fan_speed = ctrl.Consequent(np.arange(0, 101, 1), 'fan_speed')      # 0~100 %

# =========================
# 2. 定義模糊集合
# =========================
# 溫度的模糊集合
temperature['low'] = fuzz.trimf(temperature.universe, [0, 0, 20])
temperature['medium'] = fuzz.trimf(temperature.universe, [10, 20, 30])
temperature['high'] = fuzz.trimf(temperature.universe, [20, 40, 40])

# 風扇速度的模糊集合
fan_speed['low'] = fuzz.trimf(fan_speed.universe, [0, 0, 50])
fan_speed['medium'] = fuzz.trimf(fan_speed.universe, [25, 50, 75])
fan_speed['high'] = fuzz.trimf(fan_speed.universe, [50, 100, 100])

# =========================
# 3. 建立規則庫
# =========================
rule1 = ctrl.Rule(temperature['low'], fan_speed['low'])
rule2 = ctrl.Rule(temperature['medium'], fan_speed['medium'])
rule3 = ctrl.Rule(temperature['high'], fan_speed['high'])

# =========================
# 4. 建立控制系統
# =========================
fan_ctrl = ctrl.ControlSystem([rule1, rule2, rule3])
fan_sim = ctrl.ControlSystemSimulation(fan_ctrl)

# =========================
# 5. 輸入數值並推論
# =========================
fan_sim.input['temperature'] = 15
fan_sim.compute()

print(f"溫度 = 15°C")
print(f"風扇輸出 = {fan_sim.output['fan_speed']:.2f}%")

# =========================
# 6. 繪製模糊集合圖表（含註解）
# =========================
fig, axes = plt.subplots(1, 1, figsize=(10, 4))

# ---------- 圖 1：溫度模糊集合 ----------
x_temp = temperature.universe
y_temp_low = temperature['low'].mf
y_temp_medium = temperature['medium'].mf
y_temp_high = temperature['high'].mf

# axes.plot(x_temp, y_temp_low, label='low', color='#FFAE49', linestyle='-')
axes.plot(x_temp, y_temp_high, label='high', color='#024B7A', linestyle='-')
# axes.plot(x_temp, y_temp_medium, label='medium', color='#44B7C2', linestyle='-')

axes.set_title('Temperature Fuzzy Sets')
axes.set_xlabel('Temperature (°C)')
axes.set_ylabel('Membership')
axes.legend()
axes.grid(True)

# 註解 low
# axes.annotate(
#     'low\n[0, 0, 20]',
#     xy=(12, 0.4),              # 箭頭指向的位置
#     xytext=(16, 0.6),        # 文字顯示的位置
#     arrowprops=dict(arrowstyle='->')
# )

# 註解 medium
# axes.annotate(
#     'medium\n[10, 20, 30]',
#     xy=(25, 0.5),
#     xytext=(30, 0.6),
#     arrowprops=dict(arrowstyle='->')
# )

# 註解 high
axes.annotate(
    'high\n[20, 40, 40]',
    xy=(30, 0.5),
    xytext=(22, 0.7),
    arrowprops=dict(arrowstyle='->')
)

# 標示輸入值 temperature = 15
# axes.axvline(x=15, linestyle='--', color='#BFBFBF')
# axes.annotate(
#     'input = 15°C',
#     xy=(15, 0.3),
#     xytext=(17, 0.4),
#     arrowprops=dict(arrowstyle='->')
# )


# axes.plot([0, 0], [0, 1], linestyle='-', color='#FFAE49')
axes.plot([40, 40], [0, 1], linestyle='-', color='#024B7A')

# # ---------- 圖 2：風扇速度模糊集合 ----------

# fig, axes = plt.subplots(1, 1, figsize=(10, 4))

# x_fan = fan_speed.universe
# y_fan_low = fan_speed['low'].mf
# y_fan_medium = fan_speed['medium'].mf
# y_fan_high = fan_speed['high'].mf

# axes.plot(x_fan, y_fan_low, label='low')
# axes.plot(x_fan, y_fan_medium, label='medium')
# axes.plot(x_fan, y_fan_high, label='high')

# axes.set_title('Fan Speed Fuzzy Sets')
# axes.set_xlabel('Fan Speed (%)')
# axes.set_ylabel('Membership')
# axes.legend()
# axes.grid(True)

# # 註解 low
# axes.annotate(
#     'low\n[0, 0, 50]',
#     xy=(0, 1),
#     xytext=(10, 0.8),
#     arrowprops=dict(arrowstyle='->')
# )

# # 註解 medium
# axes.annotate(
#     'medium\n[25, 50, 75]',
#     xy=(50, 1),
#     xytext=(58, 0.8),
#     arrowprops=dict(arrowstyle='->')
# )

# # 註解 high
# axes.annotate(
#     'high\n[50, 100, 100]',
#     xy=(100, 1),
#     xytext=(90, 0.7),
#     arrowprops=dict(arrowstyle='->')
# )

plt.tight_layout()
plt.show()