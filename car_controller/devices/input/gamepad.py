import pygame
from typing import Tuple, Optional, Callable, Dict
from .base_input import BaseInput
import logging
import time

class Gamepad(BaseInput):
    def __init__(self, joystick_index: int = 0):
        self.joystick_index = joystick_index
        self.joystick: Optional[pygame.joystick.Joystick] = None
        self.steering_trim = 0.0
        self.trim_step = 2.0 / 90
        self.prev_dpad = (0, 0)
        self.logger = logging.getLogger(__name__)
        self.button_actions: Dict[int, Callable[[], None]] = {}
        self.rumble_supported = False

    def initialize(self) -> None:
        pygame.init()
        pygame.joystick.init()

        if pygame.joystick.get_count() == 0:
            raise RuntimeError("No gamepad found")

        self.joystick = pygame.joystick.Joystick(self.joystick_index)
        self.joystick.init()
        self.logger.info(f"Gamepad initialized: {self.joystick.get_name()}")

        # Проверка поддержки вибрации
        try:
            self.joystick.rumble(0.5, 0.5, 300)
            time.sleep(0.3)
            self.rumble_supported = True
            self.logger.info("Gamepad vibration supported")
        except pygame.error:
            self.logger.warning("Gamepad vibration not supported")

    def register_button_action(self, button_id: int, action: Callable[[], None]) -> None:
        self.button_actions[button_id] = action

    def vibrate(self, low_freq: float, high_freq: float, duration_ms: int) -> None:
        if self.rumble_supported:
            try:
                self.joystick.rumble(low_freq, high_freq, duration_ms)
                time.sleep(duration_ms / 1000.0)
            except pygame.error as e:
                self.logger.error(f"Vibration error: {e}")

    def adjust_trim_left(self) -> None:
        self.steering_trim -= self.trim_step
        self.logger.debug(f"Trim adjusted left: {self.steering_trim:.3f}")

    def adjust_trim_right(self) -> None:
        self.steering_trim += self.trim_step
        self.logger.debug(f"Trim adjusted right: {self.steering_trim:.3f}")

    def get_input(self) -> Tuple[float, float, float, bool, bool]:
        try:
            pygame.event.pump()

            # Основные элементы управления
            right_trigger = (self.joystick.get_axis(5) + 1) / 2  # Газ
            left_trigger = (self.joystick.get_axis(2) + 1) / 2   # Тормоз
            steering = self.joystick.get_axis(0)                  # Руль

            # D-pad для настройки trim
            dpad = self.joystick.get_hat(0)
            dpad_x, dpad_y = dpad
            prev_dpad_x, prev_dpad_y = self.prev_dpad

            if dpad_x == -1 and prev_dpad_x != -1:
                self.adjust_trim_left()
            if dpad_x == 1 and prev_dpad_x != 1:
                self.adjust_trim_right()

            self.prev_dpad = dpad

            # Обработка кнопок
            for button_id, action in self.button_actions.items():
                if self.joystick.get_button(button_id):
                    action()

            # Кнопки
            emergency_stop = self.joystick.get_button(7)  # Start button
            recording = self.joystick.get_button(4)       # LB button

            return (
                right_trigger,  # speed
                left_trigger,   # brake
                max(-0.5, min(0.5, steering + self.steering_trim)),  # steering
                bool(emergency_stop),
                bool(recording)
            )
        except pygame.error as e:
            self.logger.error(f"Gamepad error: {e}")
            return 0.0, 0.0, 0.0, True, False  # Безопасные значения при ошибке

    def close(self) -> None:
        if self.joystick:
            self.joystick.quit()
        pygame.quit()