import pygame
import time
from typing import Dict, Optional, Tuple
from car_control_v2.input.base import InputDevice, InputState
from car_control_v2.input.button_handler import ButtonHandler
from car_control_v2.config import GamepadConfig

class GamepadInput(InputDevice):
    """Класс для управления геймпадом."""

    def __init__(self, config: GamepadConfig, logger: Optional[logging.Logger] = None):
        super().__init__(logger)
        self.config = config
        self.joystick: Optional[pygame.joystick.Joystick] = None
        self.button_handler = ButtonHandler(logger)
        self.steering_trim = 0.0
        self.prev_dpad = (0, 0)
        self._last_update_time = 0.0
        self._update_interval = 1.0 / 60.0  # 60 FPS

    def initialize(self) -> None:
        """Инициализирует геймпад."""
        try:
            pygame.init()
            self.joystick = pygame.joystick.Joystick(self.config.joystick_index)
            self.joystick.init()
            self._is_initialized = True
            self.logger.info(f"Gamepad initialized: {self.joystick.get_name()}")
        except Exception as e:
            self._set_error(f"Failed to initialize gamepad: {e}")
            raise

    def start(self) -> None:
        """Запускает обработку ввода с геймпада."""
        if not self._is_initialized:
            raise RuntimeError("Gamepad not initialized")
        self._is_running = True
        self.logger.info("Gamepad input started")

    def stop(self) -> None:
        """Останавливает обработку ввода с геймпада."""
        self._is_running = False
        self.logger.info("Gamepad input stopped")

    def update(self) -> None:
        """Обновляет состояние геймпада."""
        if not self._is_running or not self._is_initialized:
            return

        current_time = time.time()
        if current_time - self._last_update_time < self._update_interval:
            return

        try:
            pygame.event.pump()
            
            # Получаем значения осей
            right_trigger = (self.joystick.get_axis(5) + 1) / 2
            left_trigger = (self.joystick.get_axis(2) + 1) / 2
            stick_x = self.joystick.get_axis(0)
            dpad = self.joystick.get_hat(0)

            # Обновляем состояния кнопок
            button_states = {
                4: self.joystick.get_button(4),  # LB
                5: self.joystick.get_button(5),  # RB
                7: self.joystick.get_button(7),  # Start
                0: self.joystick.get_button(0),  # A
                1: self.joystick.get_button(1),  # B
                2: self.joystick.get_button(2),  # X
                3: self.joystick.get_button(3),  # Y
            }
            self.button_handler.update_states(button_states)

            # Обработка D-pad
            dpad_x, dpad_y = dpad
            prev_dpad_x, prev_dpad_y = self.prev_dpad

            if dpad_x == -1 and prev_dpad_x != -1:
                self.adjust_trim_left()
            if dpad_x == 1 and prev_dpad_x != 1:
                self.adjust_trim_right()

            self.prev_dpad = dpad

            # Обновляем состояние
            self._state.speed = right_trigger
            self._state.brake = left_trigger
            self._state.steering = max(-0.5, min(0.5, stick_x + self.steering_trim))
            self._clear_error()

            self._last_update_time = current_time

        except Exception as e:
            self._set_error(f"Error updating gamepad state: {e}")

    def close(self) -> None:
        """Закрывает геймпад и освобождает ресурсы."""
        self.stop()
        if self.joystick:
            self.joystick.quit()
            self.joystick = None
        self._is_initialized = False
        self.logger.info("Gamepad closed")

    def register_button_action(self, button_id: int, action: Callable[[], None]) -> None:
        """Регистрирует действие для кнопки."""
        self.button_handler.register_action(button_id, action)

    def adjust_trim_left(self) -> None:
        """Уменьшает значение трима руля."""
        self.steering_trim -= self.config.trim_step
        self.logger.debug(f"Trim adjusted left: {self.steering_trim:.3f}")

    def adjust_trim_right(self) -> None:
        """Увеличивает значение трима руля."""
        self.steering_trim += self.config.trim_step
        self.logger.debug(f"Trim adjusted right: {self.steering_trim:.3f}")

    def reset_trim(self) -> None:
        """Сбрасывает значение трима руля."""
        self.steering_trim = 0.0
        self.logger.debug("Trim reset to 0.0")

    def set_steering_trim(self, trim: float) -> None:
        """Устанавливает значение трима руля."""
        self.steering_trim = trim
        self.logger.debug(f"Trim set to: {trim:.3f}") 