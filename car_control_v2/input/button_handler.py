from typing import Dict, Callable, Optional
import logging

class ButtonHandler:
    """Обработчик кнопок с поддержкой состояний и действий."""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self._button_actions: Dict[int, Callable[[], None]] = {}
        self._prev_states: Dict[int, bool] = {}
        self._current_states: Dict[int, bool] = {}

    def register_action(self, button_id: int, action: Callable[[], None]) -> None:
        """Регистрирует действие для кнопки."""
        self._button_actions[button_id] = action
        self._prev_states[button_id] = False
        self._current_states[button_id] = False
        self.logger.debug(f"Registered action for button {button_id}")

    def unregister_action(self, button_id: int) -> None:
        """Удаляет действие для кнопки."""
        if button_id in self._button_actions:
            del self._button_actions[button_id]
            del self._prev_states[button_id]
            del self._current_states[button_id]
            self.logger.debug(f"Unregistered action for button {button_id}")

    def update_states(self, button_states: Dict[int, bool]) -> None:
        """Обновляет состояния кнопок и вызывает соответствующие действия."""
        for button_id, current_state in button_states.items():
            # Инициализируем состояние, если кнопка новая
            if button_id not in self._prev_states:
                self._prev_states[button_id] = False
                self._current_states[button_id] = False

            # Сохраняем предыдущее состояние
            self._prev_states[button_id] = self._current_states[button_id]
            self._current_states[button_id] = current_state

            # Вызываем действие при нажатии (переход из False в True)
            if current_state and not self._prev_states[button_id]:
                if button_id in self._button_actions:
                    try:
                        self._button_actions[button_id]()
                        self.logger.debug(f"Executed action for button {button_id}")
                    except Exception as e:
                        self.logger.error(f"Error executing action for button {button_id}: {e}")

    def get_button_state(self, button_id: int) -> bool:
        """Возвращает текущее состояние кнопки."""
        return self._current_states.get(button_id, False)

    def is_button_pressed(self, button_id: int) -> bool:
        """Проверяет, была ли кнопка только что нажата."""
        return (self._current_states.get(button_id, False) and 
                not self._prev_states.get(button_id, False))

    def clear(self) -> None:
        """Очищает все зарегистрированные действия и состояния."""
        self._button_actions.clear()
        self._prev_states.clear()
        self._current_states.clear()
        self.logger.debug("Cleared all button actions and states") 