from abc import ABC, abstractmethod
from typing import Callable, Dict
import logging

logger = logging.getLogger(__name__)

class ButtonHandler(ABC):
    @abstractmethod
    def handle_buttons(self, button_states: Dict[int, bool]) -> None:
        pass

class GamepadButtonHandler(ButtonHandler):
    def __init__(self):
        self.button_actions: Dict[int, Callable[[], None]] = {}
        self.prev_button_states: Dict[int, bool] = {}
        logger.info("GamepadButtonHandler initialized")

    def register_action(self, button_id: int, action: Callable[[], None]) -> None:
        self.button_actions[button_id] = action
        self.prev_button_states[button_id] = False
        logger.debug(f"Action registered for button {button_id}")

    def handle_buttons(self, button_states: Dict[int, bool]) -> None:
        logger.debug(f"Handling button states: {button_states}")
        for button_id, current_state in button_states.items():
            if button_id not in self.prev_button_states:
                self.prev_button_states[button_id] = False
            if current_state and not self.prev_button_states[button_id]:
                if button_id in self.button_actions:
                    logger.info(f"Button {button_id} pressed, executing action")
                    try:
                        self.button_actions[button_id]()
                    except Exception as e:
                        logger.error(f"Error executing action for button {button_id}: {e}")
                else:
                    logger.debug(f"Button {button_id} pressed, no action registered")
            self.prev_button_states[button_id] = current_state