import pygame
from .input_device import InputDevice
from .button_handler import GamepadButtonHandler
from typing import Tuple, Callable

class GamepadInput(InputDevice):
    def __init__(self, joystick_index: int = 0):
        self.joystick_index = joystick_index
        self.joystick = None
        self.button_handler = GamepadButtonHandler()

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

    def get_input(self) -> Tuple[float, float, float, bool, bool]:
        """Получает данные с геймпада: правый триггер — газ, левый — тормоз."""
        pygame.event.pump()
        right_trigger = (self.joystick.get_axis(5) + 1) / 2  # Правая триггера (газ)
        left_trigger = (self.joystick.get_axis(2) + 1) / 2   # Левая триггера (тормоз)
        stick_x = self.joystick.get_axis(0)                  # Левый стик (руль)

        speed = right_trigger
        brake = left_trigger

        button_states = {
            4: self.joystick.get_button(4),  # Правый бампер (уменьшить передачу)
            5: self.joystick.get_button(5),  # Левый бампер (увеличить передачу)
            7: self.joystick.get_button(7),  # Кнопка Start (переключение режима)
            0: self.joystick.get_button(0),  # Кнопка A (запись)
            1: self.joystick.get_button(1),  # Кнопка B (задняя передача)
        }

        self.button_handler.handle_buttons(button_states)
        return speed, brake, stick_x, False, False

    def close(self) -> None:
        """Отключает геймпад, но не деинициализирует Pygame."""
        if self.joystick:
            self.joystick.quit()
            self.joystick = None
        print("Геймпад отключен.")