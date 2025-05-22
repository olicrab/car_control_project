import pygame
from .input_device import InputDevice
from .button_handler import GamepadButtonHandler
from typing import Tuple, Callable

class GamepadInput(InputDevice):
    def __init__(self, joystick_index: int = 0):
        self.joystick_index = joystick_index
        self.joystick = None
        self.button_handler = GamepadButtonHandler()
        self.steering_trim = 0.0  # Корректировка руля (в единицах steering: -0.5..0.5)
        self.trim_step = 2.0 / 90  # Шаг корректировки (2 в диапазоне Arduino 0–180 → ~0.0222)
        self.prev_dpad = (0, 0)   # Предыдущее состояние D-Pad для отслеживания изменений

    def initialize(self) -> None:
        """Инициализирует геймпад."""
        try:
            self.joystick = pygame.joystick.Joystick(self.joystick_index)
            self.joystick.init()
            print("Геймпад инициализирован.")
        except pygame.error as e:
            raise RuntimeError(f"Ошибка инициализации геймпада: {e}")

    def register_button_action(self, button_id: int, action: Callable[[], None]) -> None:
        """Регистрирует действие для кнопки геймпада."""
        self.button_handler.register_action(button_id, action)

    def adjust_trim_left(self) -> None:
        """Уменьшает trim (корректировка влево)."""
        self.steering_trim -= self.trim_step
        print(f"Trim уменьшен: {self.steering_trim:.3f}")

    def adjust_trim_right(self) -> None:
        """Увеличивает trim (корректировка вправо)."""
        self.steering_trim += self.trim_step
        print(f"Trim увеличен: {self.steering_trim:.3f}")

    def reset_trim(self) -> None:
        """Обнуляет trim."""
        self.steering_trim = 0.0
        print("Trim сброшен: 0.0")

    def get_input(self) -> Tuple[float, float, float, bool, bool]:
        """Получает данные с геймпада: правый триггер — газ, левый — тормоз."""
        pygame.event.pump()
        right_trigger = (self.joystick.get_axis(5) + 1) / 2  # Правая триггера (газ)
        left_trigger = (self.joystick.get_axis(2) + 1) / 2   # Левая триггера (тормоз)
        stick_x = self.joystick.get_axis(0)                  # Левый стик (руль)
        dpad = self.joystick.get_hat(0)                      # D-Pad (x, y)

        # Обработка кнопок (без D-Pad)
        button_states = {
            4: self.joystick.get_button(4),  # Правый бампер
            5: self.joystick.get_button(5),  # Левый бампер
            7: self.joystick.get_button(7),  # Start
            0: self.joystick.get_button(0),  # A
            1: self.joystick.get_button(1),  # B
        }
        self.button_handler.handle_buttons(button_states)

        # Обработка D-Pad: реагируем на новые нажатия
        dpad_x, dpad_y = dpad
        prev_dpad_x, prev_dpad_y = self.prev_dpad

        # D-Pad Left: новое нажатие (переход из 0 в -1)
        if dpad_x == -1 and prev_dpad_x != -1:
            self.adjust_trim_left()
        # D-Pad Right: новое нажатие (переход из 0 в 1)
        if dpad_x == 1 and prev_dpad_x != 1:
            self.adjust_trim_right()
        # D-Pad Up: новое нажатие (переход из 0 в 1)
        if dpad_y == 1 and prev_dpad_y != 1:
            self.reset_trim()

        # Обновляем предыдущее состояние D-Pad
        self.prev_dpad = dpad

        speed = right_trigger
        brake = left_trigger
        # Применяем trim к steering
        steering = max(-0.5, min(0.5, stick_x + self.steering_trim))

        return speed, brake, steering, False, False

    def set_steering_trim(self, trim: float) -> None:
        """Устанавливает значение trim (для синхронизации с другими устройствами)."""
        self.steering_trim = trim
        print(f"Trim установлен: {self.steering_trim:.3f}")

    def close(self) -> None:
        """Отключает геймпад, но не деинициализирует Pygame."""
        if self.joystick:
            self.joystick.quit()
            self.joystick = None
        print("Геймпад отключен.")