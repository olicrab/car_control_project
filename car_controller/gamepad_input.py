import pygame
import time
from .input_device import InputDevice
from .button_handler import GamepadButtonHandler
from typing import Tuple, Callable

class GamepadInput(InputDevice):
    def __init__(self, joystick_index: int = 0):
        self.joystick_index = joystick_index
        self.joystick = None
        self.button_handler = GamepadButtonHandler()
        self.steering_trim = 0.0
        self.trim_step = 2.0 / 90
        self.prev_dpad = (0, 0)
        self.camera_input = None
        self.rumble_supported = False

    def initialize(self) -> None:
        """Инициализирует геймпад и проверяет вибрацию."""
        try:
            self.joystick = pygame.joystick.Joystick(self.joystick_index)
            self.joystick.init()
            print("Геймпад инициализирован")
            try:
                self.joystick.rumble(0.1, 0.1, 100)
                self.rumble_supported = True
                print("Вибрация поддерживается")
            except pygame.error:
                print("Вибрация не поддерживается")
        except pygame.error as e:
            raise RuntimeError(f"Ошибка инициализации геймпада: {e}")

    def register_button_action(self, button_id: int, action: Callable[[], None]) -> None:
        self.button_handler.register_action(button_id, action)

    def vibrate(self, low_freq: float, high_freq: float, duration_ms: int) -> None:
        if self.rumble_supported:
            try:
                self.joystick.rumble(low_freq, high_freq, duration_ms)
            except pygame.error as e:
                print(f"Ошибка вибрации: {e}")

    def vibrate_on_record_start(self) -> None:
        self.vibrate(0.5, 0.5, 300)

    def vibrate_on_record_stop(self) -> None:
        self.vibrate(0.5, 0.5, 200)
        time.sleep(0.3)
        self.vibrate(0.5, 0.5, 200)

    def adjust_trim_left(self) -> None:
        self.steering_trim -= self.trim_step

    def adjust_trim_right(self) -> None:
        self.steering_trim += self.trim_step

    def reset_trim(self) -> None:
        self.steering_trim = 0.0

    def get_input(self) -> Tuple[float, float, float, bool, bool]:
        pygame.event.pump()
        right_trigger = (self.joystick.get_axis(5) + 1) / 2
        left_trigger = (self.joystick.get_axis(2) + 1) / 2
        stick_x = self.joystick.get_axis(0)
        dpad = self.joystick.get_hat(0)

        button_states = {
            4: self.joystick.get_button(4),
            5: self.joystick.get_button(5),
            7: self.joystick.get_button(7),
            0: self.joystick.get_button(0),
            1: self.joystick.get_button(1),
            2: self.joystick.get_button(2),
            3: self.joystick.get_button(3),
        }
        self.button_handler.handle_buttons(button_states)

        dpad_x, dpad_y = dpad
        prev_dpad_x, prev_dpad_y = self.prev_dpad

        if dpad_x == -1 and prev_dpad_x != -1:
            self.adjust_trim_left()
        if dpad_x == 1 and prev_dpad_x != 1:
            self.adjust_trim_right()
        if dpad_y == -1 and prev_dpad_y != -1:
            self.decrease_depth_threshold()
        if dpad_y == 1 and prev_dpad_y != 1:
            self.increase_depth_threshold()

        self.prev_dpad = dpad

        speed = right_trigger
        brake = left_trigger
        steering = max(-0.5, min(0.5, stick_x + self.steering_trim))

        return speed, brake, steering, False, False

    def set_steering_trim(self, trim: float) -> None:
        self.steering_trim = trim

    def increase_depth_threshold(self) -> None:
        if hasattr(self, 'camera_input'):
            self.camera_input.increase_depth_threshold()

    def decrease_depth_threshold(self) -> None:
        if hasattr(self, 'camera_input'):
            self.camera_input.decrease_depth_threshold()

    def reset_depth_threshold(self) -> None:
        if hasattr(self, 'camera_input'):
            self.camera_input.reset_depth_threshold()

    def set_camera_input(self, camera_input: 'ZEDCameraInput') -> None:
        self.camera_input = camera_input

    def close(self) -> None:
        if self.joystick:
            self.joystick.quit()
            self.joystick = None
        print("Геймпад отключен")