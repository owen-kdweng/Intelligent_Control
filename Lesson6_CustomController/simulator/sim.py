from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Tuple
import math
import random

import pygame


# ============================================================
# 工具函式（數學與數值處理）
# ============================================================

def clamp(x: float, lo: float, hi: float) -> float:
    """
    將數值限制在 [lo, hi] 範圍內

    常用於：
    - 限制速度
    - 限制角速度
    - 防止控制器輸出爆掉
    """
    return lo if x < lo else hi if x > hi else x


def wrap_pi(a: float) -> float:
    """
    將角度包回 (-pi, pi] 範圍

    為什麼要做？
    - 避免角度無限累積
    - 方便做角度誤差計算
    - 機器人控制非常常見

    例：
      3.5π → -0.5π
    """
    a = (a + math.pi) % (2 * math.pi) - math.pi
    return a


# ============================================================
# 模擬設定（集中管理所有視覺與比例參數）
# ============================================================

@dataclass
class SimConfig:
    """
    模擬器全域設定
    """

    # ---------------- 視窗 ----------------
    width: int = 900
    height: int = 600
    fps: int = 60

    # ---------------- 尺度 ----------------
    meters_per_pixel: float = 0.01
    # 意義：
    #   1 pixel = 0.01 m
    #   100 pixel = 1 m

    # ---------------- 顏色 ----------------
    background_color: Tuple[int, int, int] = (245, 245, 245)
    axis_color: Tuple[int, int, int] = (220, 220, 220)
    robot_color: Tuple[int, int, int] = (30, 30, 30)
    heading_color: Tuple[int, int, int] = (220, 50, 50)
    trail_color: Tuple[int, int, int] = (50, 120, 220)

    # ---------------- 顯示選項 ----------------
    show_trail: bool = True
    trail_max_points: int = 2000
    show_hud: bool = True


# ============================================================
# 世界（場地）
# ============================================================

class World:
    """
    World 負責：

    - 座標轉換（世界 ↔ 畫面）
    - 畫背景
    - 畫座標軸
    - 管理終點 goal
    - 管理中繼點 waypoints
    - 用順序記憶方式追蹤目前路徑進度
    """

    def __init__(self, config: SimConfig, origin_px: Optional[Tuple[int, int]] = None):
        self.cfg = config

        # 畫面上「世界原點」的位置
        # 預設在畫面中央
        self.origin_px = (
            origin_px
            if origin_px is not None
            else (config.width // 2, config.height // 2)
        )

        # 終點（最後目標）
        self.goal: Optional[Tuple[float, float]] = None

        # 中繼點（依序前往）
        self.waypoints: list[Tuple[float, float]] = []

        # 目前路徑進度索引
        # 0 表示還沒通過任何點
        self.current_path_index: int = 0

    # --------------------------------------------------------
    # 座標轉換：世界(m) → 畫面(px)
    # --------------------------------------------------------
    def world_to_screen(self, x_m: float, y_m: float) -> Tuple[int, int]:
        """
        世界座標系：

            x → 右
            y → 上

        pygame 畫面座標：

            x → 右
            y → 下  ← 注意這裡相反！
        """
        ox, oy = self.origin_px

        px = int(ox + x_m / self.cfg.meters_per_pixel)
        py = int(oy - y_m / self.cfg.meters_per_pixel)

        return px, py

    # --------------------------------------------------------
    # 座標轉換：畫面(px) → 世界(m)
    # --------------------------------------------------------
    def screen_to_world(self, px: int, py: int) -> Tuple[float, float]:
        ox, oy = self.origin_px

        x_m = (px - ox) * self.cfg.meters_per_pixel
        y_m = (oy - py) * self.cfg.meters_per_pixel

        return x_m, y_m

    # --------------------------------------------------------
    # 設定終點
    # --------------------------------------------------------
    def set_goal(self, x_m: float, y_m: float) -> None:
        """設定終點（世界座標，單位 m）"""
        self.goal = (x_m, y_m)
        self.current_path_index = 0

    # --------------------------------------------------------
    # 清除終點
    # --------------------------------------------------------
    def clear_goal(self) -> None:
        """
        清除終點，並一併清除所有中繼點與路徑進度
        因為規則是：沒有終點就不能有中繼點
        """
        self.goal = None
        self.waypoints.clear()
        self.current_path_index = 0

    # --------------------------------------------------------
    # 設定多個中繼點
    # --------------------------------------------------------
    def set_waypoints(self, points: list[Tuple[float, float]]) -> None:
        """
        設定中繼點，必須先有終點
        """
        if self.goal is None:
            raise ValueError("必須先設定終點，才能設定中繼點")

        self.waypoints = list(points)
        self.current_path_index = 0

    # --------------------------------------------------------
    # 新增單一中繼點
    # --------------------------------------------------------
    def add_waypoint(self, x_m: float, y_m: float) -> None:
        """
        新增單一中繼點，必須先有終點
        """
        if self.goal is None:
            raise ValueError("必須先設定終點，才能新增中繼點")

        self.waypoints.append((x_m, y_m))

    # --------------------------------------------------------
    # 清除所有中繼點
    # --------------------------------------------------------
    def clear_waypoints(self) -> None:
        """
        清除所有中繼點，並重置路徑進度
        """
        self.waypoints.clear()
        self.current_path_index = 0

    # --------------------------------------------------------
    # 取得完整路徑（中繼點 + 終點）
    # --------------------------------------------------------
    def get_full_path_points(self) -> list[Tuple[float, float]]:
        """
        回傳完整路徑：
        [waypoint1, waypoint2, ..., goal]
        """
        if self.goal is None:
            return []

        return self.waypoints + [self.goal]

    # --------------------------------------------------------
    # 更新路徑進度（順序記憶）
    # --------------------------------------------------------
    def update_path_progress(
        self,
        robot_x: float,
        robot_y: float,
        reach_threshold: float = 0.1
    ) -> None:
        """
        用順序記憶方式更新目前進度：

        - 只檢查「目前目標點」
        - 若已接近目前目標點，索引才往下一個推進
        - 不會因為靠近後面的點，就跳過前面的點
        """
        full_path = self.get_full_path_points()
        if not full_path:
            return

        while self.current_path_index < len(full_path):
            tx, ty = full_path[self.current_path_index]
            dist = math.hypot(tx - robot_x, ty - robot_y)

            if dist <= reach_threshold:
                self.current_path_index += 1
            else:
                break

    # --------------------------------------------------------
    # 取得剩餘路徑點
    # --------------------------------------------------------
    def get_path_points(
        self,
        robot_x: float,
        robot_y: float,
        reach_threshold: float = 0.1
    ) -> list[Tuple[float, float]]:
        """
        依機器人目前位置，自動更新進度後，
        回傳「尚未經過」的路徑點。

        例如：
        - 若已經通過前兩個中繼點
        - 就只回傳 [第三個中繼點, ..., goal]
        """
        full_path = self.get_full_path_points()
        if not full_path:
            return []

        self.update_path_progress(robot_x, robot_y, reach_threshold)
        return full_path[self.current_path_index:]

    # --------------------------------------------------------
    # 取得目前目標點
    # --------------------------------------------------------
    def get_current_target(
        self,
        robot_x: float,
        robot_y: float,
        reach_threshold: float = 0.1
    ) -> Optional[Tuple[float, float]]:
        """
        回傳目前應該追蹤的目標點。
        若全部走完則回傳 None。
        """
        remaining = self.get_path_points(robot_x, robot_y, reach_threshold)
        return remaining[0] if remaining else None

    # --------------------------------------------------------
    # 是否已完成整條路徑
    # --------------------------------------------------------
    def is_path_completed(
        self,
        robot_x: float,
        robot_y: float,
        reach_threshold: float = 0.1
    ) -> bool:
        """
        判斷是否所有中繼點與終點都已完成
        """
        remaining = self.get_path_points(robot_x, robot_y, reach_threshold)
        return len(remaining) == 0

    # --------------------------------------------------------
    # 畫背景
    # --------------------------------------------------------
    def draw(self, screen: pygame.Surface) -> None:
        """
        畫出：

        - 背景
        - 座標軸
        - 網格（1m）
        - 中繼點
        - 終點旗子
        """
        screen.fill(self.cfg.background_color)

        ox, oy = self.origin_px

        # 畫 X 軸
        pygame.draw.line(
            screen, self.cfg.axis_color, (0, oy), (self.cfg.width, oy), 1
        )

        # 畫 Y 軸
        pygame.draw.line(
            screen, self.cfg.axis_color, (ox, 0), (ox, self.cfg.height), 1
        )

        # 畫 1m 網格
        step_px = int(1.0 / self.cfg.meters_per_pixel)

        if 0 < step_px < 2000:
            for x in range(ox % step_px, self.cfg.width, step_px):
                pygame.draw.line(
                    screen, self.cfg.axis_color, (x, 0), (x, self.cfg.height), 1
                )

            for y in range(oy % step_px, self.cfg.height, step_px):
                pygame.draw.line(
                    screen, self.cfg.axis_color, (0, y), (self.cfg.width, y), 1
                )

        # 畫中繼點與終點
        if self.goal is not None:
            self._draw_waypoints(screen)
            self._draw_goal_flag(screen)

    # --------------------------------------------------------
    # 繪製中繼點
    # --------------------------------------------------------
    def _draw_waypoints(self, screen: pygame.Surface) -> None:
        """
        畫中繼點：
        - 未到達：藍色
        - 已經通過：淡灰藍色
        """
        for i, (wx, wy) in enumerate(self.waypoints):
            x_px, y_px = self.world_to_screen(wx, wy)

            already_passed = i < self.current_path_index

            if already_passed:
                fill_color = (170, 190, 220)
                border_color = (120, 140, 170)
            else:
                fill_color = (50, 120, 220)
                border_color = (20, 60, 140)

            pygame.draw.circle(screen, fill_color, (x_px, y_px), 6)
            pygame.draw.circle(screen, border_color, (x_px, y_px), 6, 2)

    # --------------------------------------------------------
    # 繪製終點旗幟
    # --------------------------------------------------------
    def _draw_goal_flag(self, screen: pygame.Surface) -> None:
        """
        畫一個紅色小旗子作為終點標示
        """
        assert self.goal is not None
        gx, gy = self.goal
        x_px, y_px = self.world_to_screen(gx, gy)

        # 旗桿高度（像素）
        pole_h = 35
        pole_w = 2

        # 旗桿（深灰）
        pole_color = (80, 80, 80)
        pygame.draw.rect(
            screen,
            pole_color,
            (x_px - pole_w // 2, y_px - pole_h, pole_w, pole_h)
        )

        # 旗子（三角形，紅色）
        flag_color = (220, 40, 40)
        p1 = (x_px, y_px - pole_h)
        p2 = (x_px + 22, y_px - pole_h + 8)
        p3 = (x_px, y_px - pole_h + 16)
        pygame.draw.polygon(screen, flag_color, [p1, p2, p3])

        # 底座（小圓點）
        pygame.draw.circle(screen, flag_color, (x_px, y_px), 4)

# ============================================================
# 二輪差速機器人（運動學模型）
# ============================================================

class DifferentialDriveRobot:
    """
    二輪差速車（unicycle kinematics）

    控制輸入：

        v : 線速度 (m/s)
        w : 角速度 (rad/s)

    狀態：

        x, y : 位置 (m)
        theta : 朝向 (rad)
    """

    def __init__(
        self,
        x: float = 0.0,
        y: float = 0.0,
        theta: float = 0.0,
        radius_m: float = 0.12,
        v_limit: float = 1.0,
        w_limit: float = 2.5,
        # 誤差
        noise_enabled: bool = False,
        v_noise: float = 0.02,     # 速度比例
        w_noise: float = 0.05,     # 加速度比例
        v_bias: float = 0.0,         # m/s（系統性偏差）
        w_bias: float = 0.0,          # rad/s
        # 編碼器
        wheel_base_m: float = 0.24,      # 輪距 L（左右輪中心距），單位 m
        wheel_radius_m: float = 0.03,    # 輪半徑 r，單位 m
        ticks_per_rev: int = 360,        # 每轉一圈的 ticks（理想編碼器）
        encoder_enabled: bool = True,    # 是否啟用編碼器
        # 外觀
        body_color: Tuple[int, int, int] = (30, 30, 30),
        wheel_color: Tuple[int, int, int] = (40, 40, 40),
        heading_color: Tuple[int, int, int] = (220, 50, 50),
    ):
        # ---------------- 位姿 ----------------
        self.x = x
        self.y = y
        self.theta = theta

        # ---------------- 實際速度狀態（有慣性）----------------
        self.v = 0.0          # 真正線速度
        self.w = 0.0          # 真正角速度

        # ---------------- 慣性參數 ----------------
        self.use_inertia = True
        self.tau_v = 1.0     # 線速度時間常數（秒）
        self.tau_w = 0.5     # 角速度時間常數（秒）

        # 可選：加速度上限，避免數值太猛
        self.a_limit = 0.4    # m/s^2
        self.alpha_limit = 0.8  # rad/s^2

        # ---------------- 外觀 ----------------
        self.radius_m = radius_m
        self.body_color = body_color
        self.wheel_color = wheel_color
        self.heading_color = heading_color

        # ---------------- 控制限制 ----------------
        self.v_limit = v_limit
        self.w_limit = w_limit

        # ---------------- 當前指令 ----------------
        self.v_cmd = 0.0
        self.w_cmd = 0.0

        # ---------------- 軌跡 ----------------
        self._trail = []

        # ---------------- 速度與角速度誤差 ----------------
        self.noise_enabled = noise_enabled
        self.v_noise = v_noise
        self.w_noise = w_noise
        self.v_bias = v_bias
        self.w_bias = w_bias

        # ---------------- 編碼器（理想、無誤差）----------------
        self.encoder_enabled = encoder_enabled
        self.wheel_base_m = wheel_base_m 
        self.wheel_radius_m = wheel_radius_m
        self.ticks_per_rev = ticks_per_rev

        # 累積值：用 float 存，保持「無誤差」（不做量化誤差）
        self.left_ticks = 0.0
        self.right_ticks = 0.0

        # 也順便存「輪子累積轉角（rad）」方便你教學
        self.left_wheel_rad = 0.0
        self.right_wheel_rad = 0.0


    # --------------------------------------------------------
    # 設定控制命令
    # --------------------------------------------------------
    def set_command(self, v: float, w: float) -> None:
        ev = v
        ew = w
        if self.noise_enabled and (v!=0 or w!=0):
            v_noise = abs(v*self.v_noise) if v!=0 else abs(random.gauss(0, 0.3))
            w_noise = abs(w*self.w_noise) if w!=0 else abs(random.gauss(0, 0.3))
            ev = random.gauss(v, v_noise)
            ew = random.gauss(w, w_noise)

            max_v = abs(v)+v_noise
            max_w = abs(w)+w_noise
            ev = clamp(ev, -max_v, max_v) + self.v_bias
            ew = clamp(ew, -max_w, max_w) + self.w_bias
                
        self.v_cmd = clamp(ev, -self.v_limit, self.v_limit)
        self.w_cmd = clamp(ew, -self.w_limit, self.w_limit)

    # --------------------------------------------------------
    # 動力學更新（Euler integration）
    # --------------------------------------------------------
    def step(self, dt: float) -> None:
        """
        加入一階慣性：
            dv/dt = (v_cmd - v) / tau_v
            dw/dt = (w_cmd - w) / tau_w
        """

        if self.use_inertia:
            # 一階慣性
            a_v = (self.v_cmd - self.v) / max(self.tau_v, 1e-6)
            a_w = (self.w_cmd - self.w) / max(self.tau_w, 1e-6)

            # 加速度限制（可選，但很實用）
            a_v = clamp(a_v, -self.a_limit, self.a_limit)
            a_w = clamp(a_w, -self.alpha_limit, self.alpha_limit)

            # Euler 積分更新「實際速度」
            self.v += a_v * dt
            self.w += a_w * dt
        else:
            # 不使用慣性時，退回原本行為
            self.v = self.v_cmd
            self.w = self.w_cmd

        # 再用「實際速度」更新位姿
        v = self.v
        w = self.w

        self.x += v * math.cos(self.theta) * dt
        self.y += v * math.sin(self.theta) * dt
        self.theta = wrap_pi(self.theta + w * dt)

        # ---- 編碼器更新也要用實際速度，不要用命令速度 ----
        if self.encoder_enabled:
            L = self.wheel_base_m
            r = self.wheel_radius_m

            v_l = v - w * (L / 2.0)
            v_r = v + w * (L / 2.0)

            omega_l = v_l / r
            omega_r = v_r / r

            dphi_l = omega_l * dt
            dphi_r = omega_r * dt

            self.left_wheel_rad += dphi_l
            self.right_wheel_rad += dphi_r

            ticks_per_rad = self.ticks_per_rev / (2.0 * math.pi)
            self.left_ticks += dphi_l * ticks_per_rad
            self.right_ticks += dphi_r * ticks_per_rad

    # --------------------------------------------------------
    # 重設編碼器
    # --------------------------------------------------------
    def reset_encoders(self) -> None:
        self.left_ticks = 0.0
        self.right_ticks = 0.0
        self.left_wheel_rad = 0.0
        self.right_wheel_rad = 0.0

    # --------------------------------------------------------
    # 讀取編碼器
    # --------------------------------------------------------
    def get_encoders(self):
        """
        回傳理想編碼器讀值（無誤差）
        - ticks 用 float：代表「真實累積」，不引入量化誤差
        - 如果你想要整數 ticks，可在外部用 int(round())
        """
        return int(self.left_ticks), int(self.right_ticks)

    # --------------------------------------------------------
    # 記錄軌跡
    # --------------------------------------------------------
    def record_trail(self, max_points: int) -> None:
        self._trail.append((self.x, self.y))

        if len(self._trail) > max_points:
            self._trail = self._trail[-max_points:]

    def clear_trail(self) -> None:
        self._trail.clear()

    # --------------------------------------------------------
    # 畫機器人
    # --------------------------------------------------------
    def draw(self, screen: pygame.Surface, world: World, cfg: SimConfig) -> None:
        """
        畫出：

        - 軌跡
        - 圓形車體
        - 朝向箭頭
        """

        # ---------- 軌跡 ----------
        if cfg.show_trail and len(self._trail) >= 2:
            pts = [world.world_to_screen(x, y) for (x, y) in self._trail]
            pygame.draw.lines(screen, cfg.trail_color, False, pts, 2)

        # ---------- 車體 ----------
        cx, cy = world.world_to_screen(self.x, self.y)
        # 半徑
        r_px = max(2, int(self.radius_m / cfg.meters_per_pixel))

        # 建立透明 surface
        size = r_px * 2 + 4
        body_surf = pygame.Surface((size, size), pygame.SRCALPHA)

        # 半透明填色（⭐ alpha 用 0~255）
        fill_color = (*self.body_color, 160)
        pygame.draw.circle(body_surf, fill_color, (size // 2, size // 2), r_px)

        # 外框（不透明）
        pygame.draw.circle(body_surf, self.body_color, (size // 2, size // 2), r_px, 2)

        # 貼回主畫面
        screen.blit(body_surf, (cx - size // 2, cy - size // 2))

        # ---------- 朝向 ----------
        hx = self.x + self.radius_m * 1.5 * math.cos(self.theta)
        hy = self.y + self.radius_m * 1.5 * math.sin(self.theta)
        hx_px, hy_px = world.world_to_screen(hx, hy)

        # ---------- 畫輪子 ----------
        # 輪子尺寸（你可以微調）
        wheel_width_m = self.wheel_base_m * 0.1
        wheel_length_m = self.radius_m * 0.7

        # 左右輪在車體座標的 y 偏移
        half_L = self.wheel_base_m / 2.0

        # 車體方向的單位向量
        cos_t = math.cos(self.theta)
        sin_t = math.sin(self.theta)

        # 計算左右輪中心（世界座標）
        # 車體側向單位向量（左方向）
        side_x = -sin_t
        side_y =  cos_t

        # 左輪中心
        lx = self.x + side_x * half_L
        ly = self.y + side_y * half_L

        # 右輪中心
        rx = self.x - side_x * half_L
        ry = self.y - side_y * half_L

        # 畫輪子（用旋轉矩形）
        self._draw_wheel(screen, world, lx, ly, wheel_length_m, wheel_width_m)
        self._draw_wheel(screen, world, rx, ry, wheel_length_m, wheel_width_m)

        pygame.draw.line(screen, self.heading_color, (cx, cy), (hx_px, hy_px), 3)

    def _draw_wheel(self, screen, world, cx_m, cy_m, length_m, width_m):
        """
        在 (cx_m, cy_m) 畫一個「跟著車身方向 θ」的矩形輪子（用四個角點畫 polygon）
        這個方式不依賴 rotate surface，因此不會出現「看起來沒轉」的視覺問題
        """

        # 世界座標中：車身前進方向（forward）與側向（side）單位向量
        cos_t = math.cos(self.theta)
        sin_t = math.sin(self.theta)

        # forward：車頭方向
        fx, fy = cos_t, sin_t

        # side：車身左側方向
        sx, sy = -sin_t, cos_t

        # 半長、半寬（公尺）
        hl = length_m / 2.0
        hw = width_m / 2.0

        # 四個角點（世界座標）
        # p = center ± forward*hl ± side*hw
        p1 = (cx_m + fx * hl + sx * hw, cy_m + fy * hl + sy * hw)  # 前左
        p2 = (cx_m + fx * hl - sx * hw, cy_m + fy * hl - sy * hw)  # 前右
        p3 = (cx_m - fx * hl - sx * hw, cy_m - fy * hl - sy * hw)  # 後右
        p4 = (cx_m - fx * hl + sx * hw, cy_m - fy * hl + sy * hw)  # 後左

        # 轉成畫面座標
        pts = [
            world.world_to_screen(*p1),
            world.world_to_screen(*p2),
            world.world_to_screen(*p3),
            world.world_to_screen(*p4),
        ]

        # 畫輪子
        pygame.draw.polygon(screen, self.wheel_color, pts)

# ============================================================
# Simulator（pygame 主迴圈封裝）
# ============================================================

class Simulator:
    """
    pygame 輕量封裝器
    - 使用者可以自己寫控制器
    - 使用者可以自己建 world / robot
    """

    def __init__(self, config: Optional[SimConfig] = None, title: str = "Robot Sim"):
        self.cfg = config if config is not None else SimConfig()
        self.title = title

        self._screen: Optional[pygame.Surface] = None
        self._clock: Optional[pygame.time.Clock] = None
        self._font: Optional[pygame.font.Font] = None
        self._running = False

        # 模擬時間
        self.sim_time = 0.0
        self.arrival_time: Optional[float] = None
        # 模擬時間判斷可調參數
        self.goal_reach_threshold = 0.08   # m，距離終點小於這個值算接近
        self.stop_v_threshold = 0.03       # m/s，線速度小於這個值算停止
        self.stop_w_threshold = 0.05       # rad/s，角速度小於這個值算停止

    @property
    def screen(self) -> pygame.Surface:
        if self._screen is None:
            raise RuntimeError("Simulator not initialized. Call sim.init_pygame() first.")
        return self._screen

    # --------------------------------------------------------
    # 初始化 pygame
    # --------------------------------------------------------
    def init_pygame(self) -> None:
        pygame.init()
        pygame.display.set_caption(self.title)

        self._screen = pygame.display.set_mode(
            (self.cfg.width, self.cfg.height)
        )
        self._clock = pygame.time.Clock()
        self._font = pygame.font.Font(None, 24)
        self._running = True

    def quit(self) -> None:
        self._running = False
        pygame.quit()

    # --------------------------------------------------------
    # 處理關閉事件
    # --------------------------------------------------------
    def handle_quit_events(self) -> bool:
        """
        回傳 False 表示使用者要求離開
        """
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return False
        return True

    # --------------------------------------------------------
    # 計算 dt
    # --------------------------------------------------------
    def tick_dt(self) -> float:
        """
        回傳每一幀經過的秒數
        """
        if self._clock is None:
            raise RuntimeError("Simulator not initialized.")

        dt_ms = self._clock.tick(self.cfg.fps)
        return dt_ms / 1000.0

    # --------------------------------------------------------
    # HUD 顯示
    # --------------------------------------------------------
    def draw_hud(self, robot: DifferentialDriveRobot, world: Optional[World] = None) -> None:
        if not self.cfg.show_hud or self._font is None:
            return

        lines_left = [
            f"v_cmd: {robot.v_cmd:+.2f}   w_cmd: {robot.w_cmd:+.2f}",
            f"v_act: {robot.v:+.2f}   w_act: {robot.w:+.2f}",
            f"pose: x={robot.x:+.2f} m  y={robot.y:+.2f} m  th={math.degrees(robot.theta):+.1f} deg",
        ]

        # 左上角顯示
        y = 8
        for s in lines_left:
            surf = self._font.render(s, True, (10, 10, 10))
            self.screen.blit(surf, (8, y))
            y += 22

        # 右上角顯示 goal 誤差
        if world is not None and world.goal is not None:
            gx, gy = world.goal
            dx = gx - robot.x
            dy = gy - robot.y
            dist = math.hypot(dx, dy)

            right_lines = [
                "Goal error (world frame):",
                f"dx = {dx:+.3f} m",
                f"dy = {dy:+.3f} m",
                f"dis = {dist:+.3f} m",
                f"sim time = {self.sim_time:.2f} s",
            ]

            if self.arrival_time is not None:
                right_lines.append(f"arrival time = {self.arrival_time:.2f} s")

            margin = 8
            y2 = 8
            for s in right_lines:
                surf = self._font.render(s, True, (10, 10, 10))
                x2 = self.cfg.width - surf.get_width() - margin
                self.screen.blit(surf, (x2, y2))
                y2 += 22

    def _check_goal_arrival(self, robot: DifferentialDriveRobot, world: Optional[World]) -> None:
        if world is None or world.goal is None:
            return

        if self.arrival_time is not None:
            return

        gx, gy = world.goal
        dist = math.hypot(gx - robot.x, gy - robot.y)

        stopped = (
            abs(robot.v) <= self.stop_v_threshold and
            abs(robot.w) <= self.stop_w_threshold
        )

        if dist <= self.goal_reach_threshold and stopped:
            self.arrival_time = self.sim_time



    # --------------------------------------------------------
    # 預設主迴圈
    # --------------------------------------------------------
    def run(
        self,
        world: World,
        robot: DifferentialDriveRobot,
        control_callback,
        *,
        draw_callback=None,
    ) -> None:
        """
        預設模擬主迴圈
        """

        if self._screen is None:
            self.init_pygame()

        while self._running:
            if not self.handle_quit_events():
                break

            dt = self.tick_dt()
            self.sim_time += dt

            # 使用者控制器
            control_callback(dt, robot)

            # 機器人運動
            robot.step(dt)
            robot.record_trail(self.cfg.trail_max_points)
            self._check_goal_arrival(robot, world)

            # 繪圖
            world.draw(self.screen)
            robot.draw(self.screen, world, self.cfg)

            if draw_callback is not None:
                draw_callback(self.screen, world, robot)

            self.draw_hud(robot, world)
            pygame.display.flip()

        self.quit()