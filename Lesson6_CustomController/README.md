# Lesson 6 : Custom Controller

## 1. 課程目標
  1. 自訂義自己的控制器
  2. 再次熟悉模糊控制


## 2. 操作指令
```bash
cd Lesson6_CustomController
python3 main.py
```


## 3. 課程步驟
  1. 了解並使用[控制器模板](./controller/controller_template.py)
  2. 參考[ PID 控制器範例](./controller/pid_controller.py)
  3. 實現[ Fuzzy 控制器](../Lesson5_FuzzyControl/)
  4. 在[ main.py ](./main.py)中引用並使用



## 4. 課堂練習
依照 [Lessin5](../Lesson5_FuzzyControl/) 的理論與實作，實現一個模糊控制器，控制模擬器的差速驅動機器人。

## 5. 學習目標
  1. 實現模糊控制器控制差速驅動機器人
  2. 重新理解模糊控制


## 6. 評分規則
| 方法                          | 分數       |
| ----------------------------- | --------- |
| 將模糊控制器實現於主程式中 [main.py](./main.py) 中      | 70以上     |
| 實現於 [controller_template.py](./controller/controller_template.py), 部分功能可在主程式定義      | 80以上     |
| 實現於 [controller_template.py](./controller/controller_template.py) , 並且可以在主程式定義模糊集合與規則等參數       | 90以上     |