import simulator as sim
import math
from controller.pid_controller import PIDController


""" ==========================================================================
# 全局變數
=========================================================================== """
timer = False
time_now = None
goal_reached = False

# 編碼器相關變數
prev_lt = prev_rt = None
x = y = theta = 0.0


""" ==========================================================================
# 工具函式
=========================================================================== """
def radians2degrees(radians: float):
    return radians*180.0/math.pi

def wrap_to_pi(angle: float) -> float:
    """將角度包回 [-pi, pi]"""
    return (angle + math.pi) % (2.0 * math.pi) - math.pi


""" ==========================================================================
# PID 控制器參數設定
=========================================================================== """
# 距離 PID -> 控制 v
dist_pid = PIDController(
    kp=10.0,
    ki=0.2,
    kd=9.6,
    output_limit=0.8,      # 最大線速度
    integral_limit=1.0
)

# 角度 PID -> 控制 w
angle_pid = PIDController(
    kp=11.0,
    ki=5.0,
    kd=9.8,
    output_limit=1.0,      # 最大角速度
    integral_limit=1.0
)



"""==========================================================================
控制器
=========================================================================="""
def controller(dt: float, robot: sim.DifferentialDriveRobot, world: sim.World):
    global timer
    global time_now
    global goal_reached
    global prev_lt, prev_rt, x, y, theta

    lt, rt = robot.get_encoders()

    if prev_lt is None:
        prev_lt = lt
        prev_rt = rt
        return

    dlt = lt - prev_lt
    drt = rt - prev_rt

    dl = 2 * math.pi * robot.wheel_radius_m * dlt / robot.ticks_per_rev
    dr = 2 * math.pi * robot.wheel_radius_m * drt / robot.ticks_per_rev

    ds = (dr + dl) / 2.0
    dtheta = (dr - dl) / robot.wheel_base_m

    x += ds * math.cos(theta + dtheta / 2.0)
    y += ds * math.sin(theta + dtheta / 2.0)
    theta = theta + dtheta

    prev_lt, prev_rt = lt, rt

    #==================================================
    # 取得目前尚未完成的路徑點
    path = world.get_path_points(x, y, reach_threshold=0.05)

    # 如果全部走完就停止
    if not path:
        robot.set_command(0.0, 0.0)
        if not goal_reached:
            goal_reached = True
            dist_pid.reset()
            angle_pid.reset()
            print("All waypoints and goal reached!")
        return

    # 目前要追的目標點
    target_x, target_y = path[0]

    #==================================================
    # 閉迴路控制：前往目前目標點
    dx = target_x - x
    dy = target_y - y

    dist_error = math.sqrt(dx * dx + dy * dy)
    target_theta = math.atan2(dy, dx)
    angle_error = wrap_to_pi(target_theta - theta)

    #==================================================
    # 到達目前目標點
    pos_tolerance = 0.05

    if goal_reached:
        robot.set_command(0.0, 0.0)
        return

    #==================================================
    # PID 控制
    w = angle_pid.update(angle_error, dt)
    v = dist_pid.update(dist_error, dt)

    robot.set_command(v, w)





"""==========================================================================
# 主程式
=========================================================================="""
def main():
    cfg = sim.SimConfig(width=1000, height=650, meters_per_pixel=0.01, fps=30)
    app = sim.Simulator(cfg, title="Diff-Drive Robot (v,w control)")

    world = sim.World(cfg)
    world.set_goal(4.0, -1.0)
    world.set_waypoints([
        (1.0, 1.0),
        (2.0, -1.0),
        (3.0, 1.0),
    ])

    robot = sim.DifferentialDriveRobot(
        x=0.0, y=0.0, theta=0.0, radius_m=0.25,
        wheel_base_m=0.50,
        wheel_radius_m=0.03,
        body_color=(70, 130, 200),
        wheel_color=(30, 30, 30),
        heading_color=(255, 20, 0),
        noise_enabled=True,
        v_noise=0.03,
        w_noise=0.03,
        v_bias=0.0,
        w_bias=0.0,
        encoder_enabled=True,
        ticks_per_rev=360,
    )

    app.run(
        world=world,
        robot=robot,
        control_callback=lambda dt, robot: controller(dt, robot, world)
    )



if __name__ == "__main__":
    main()