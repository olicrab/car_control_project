from abc import ABC, abstractmethod
from typing import Callable, Dict


class ButtonHandler(ABC):
    """Абстрактный класс для обработки кнопок."""

    @abstractmethod
    def handle_buttons(self, button_states: Dict[int, bool]) -> None:
        """Обрабатывает состояния кнопок."""
        pass


class GamepadButtonHandler(ButtonHandler):
    """Обработчик кнопок геймпада."""

    def __init__(self):
        self.button_actions: Dict[int, Callable[[], None]] = {}
        self.prev_button_states: Dict[int, bool] = {}

    def register_action(self, button_id: int, action: Callable[[], None]) -> None:
        """Регистрирует действие для кнопки."""
        self.button_actions[button_id] = action
        self.prev_button_states[button_id] = False

    def handle_buttons(self, button_states: Dict[int, bool]) -> None:
        """Обрабатывает нажатия кнопок, вызывая действия только при переходе в нажатое состояние."""
        for button_id, current_state in button_states.items():
            if button_id not in self.prev_button_states:
                self.prev_button_states[button_id] = False

            # Вызываем действие только при нажатии (переход из False в True)
            if current_state and not self.prev_button_states[button_id]:
                if button_id in self.button_actions:
                    self.button_actions[button_id]()

            self.prev_button_states[button_id] = current_state