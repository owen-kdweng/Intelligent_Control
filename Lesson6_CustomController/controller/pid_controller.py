class PIDController:
    def __init__(self, kp, ki, kd, output_limit=None, integral_limit=None):
        self.kp = kp
        self.ki = ki
        self.kd = kd

        self.output_limit = output_limit
        self.integral_limit = integral_limit

        self.integral = 0.0
        self.prev_error = 0.0
        self.initialized = False

    def reset(self):
        self.integral = 0.0
        self.prev_error = 0.0
        self.initialized = False

    def update(self, error, dt):
        if dt <= 1e-6:
            return 0.0

        if not self.initialized:
            self.prev_error = error
            self.initialized = True

        # I term
        self.integral += error * dt
        if self.integral_limit is not None:
            self.integral = max(-self.integral_limit,
                                min(self.integral, self.integral_limit))

        # D term
        derivative = (error - self.prev_error) / dt
        self.prev_error = error

        # PID output
        u = self.kp * error + self.ki * self.integral + self.kd * derivative

        if self.output_limit is not None:
            u = max(-self.output_limit, min(u, self.output_limit))

        return u
