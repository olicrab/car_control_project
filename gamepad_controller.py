import pygame

class GamepadController:
    def __init__(self):
        pygame.init()
        self.joystick = pygame.joystick.Joystick(0)
        self.joystick.init()

    def get_input(self):
        """Получаем значения триггеров и стиков с геймпада."""
        # Получаем значения с триггеров (оси 2 и 5)
        left_trigger = (self.joystick.get_axis(2) + 1) / 2  # Левый триггер (ось 2)
        right_trigger = (self.joystick.get_axis(5) + 1) / 2  # Правый триггер (ось 5)

        # Получаем значения с левого стика
        # Левый стик по оси X (влево/вправо)
        stick_x = self.joystick.get_axis(0)  # -1 (влево) до 1 (вправо)

        return right_trigger, left_trigger, stick_x

    def get_button_press(self):
        """Получаем информацию о нажатии кнопок."""
        button_left_bumper = self.joystick.get_button(4)  # Левый бампер
        button_right_bumper = self.joystick.get_button(5)  # Правый бампер
        return button_left_bumper, button_right_bumper
