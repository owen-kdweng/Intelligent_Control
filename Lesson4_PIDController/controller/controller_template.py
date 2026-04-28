class BaseController:
    """
    最小控制器框架
    範例可參考PIDController，實作一個簡單的 PID 控制器。
    """
    def __init__(self):
        """
        初始化控制器內部狀態。
            - 如果控制器需要參數，可以在此處添加，例如 PID 的 kp, ki, kd。
        """

    def reset(self):
        """
        重置控制器內部狀態。
        如果控制器不需要記憶狀態，可以留空。
        """

    def update(self, error, dt):
        """
        根據誤差與時間間隔，回傳控制輸出。

        參數：
        error : float
            目標值與目前值的差，例如 target - current

        dt : float
            時間間隔

        回傳：
        u : float
            控制輸出
        """
        return u
    

    
if __name__ == "__main__":
    # 測試控制器
    controller = BaseController()
    error = 1.0
    dt = 0.1
    output = controller.update(error, dt)
    print(f"Control output: {output}")