import pygame
import multiprocessing
from typing import Callable, Dict
from src.utils.config import ConfigManager
from src.utils.logger import Logger

class GamepadManager:
    def __init__(self, input_queue, control_mode_queue):
        pygame.init()
        self.config = ConfigManager()
        self.logger = Logger()
        self.input_queue = input_queue
        self.control_mode_queue = control_mode_queue

        self.joystick = None
        self.button_actions: Dict[int, Callable] = {}
        self._initialize_gamepad()
        self._setup_button_actions()

    def _initialize_gamepad(self):
        try:
            pygame.joystick.init()
            if pygame.joystick.get_count() > 0:
                self.joystick = pygame.joystick.Joystick(0)
                self.joystick.init()
                self.logger.info("Gamepad initialized successfully")
            else:
                self.logger.warning("No gamepad detected")
        except Exception as e:
            self.logger.error(f"Gamepad initialization error: {e}")

    def _setup_button_actions(self):
        autopilot_button = self.config.get('gamepad.autopilot_button', 7)

        self.button_actions = {
            autopilot_button: self._toggle_autopilot,
            # Другие кнопки и их действия
        }

    def _toggle_autopilot(self):
        self.logger.info("Toggling Autopilot")
        self.control_mode_queue.put('TOGGLE_AUTOPILOT')

    def process_gamepad_input(self):
        if not self.joystick:
            return None

        pygame.event.pump()

        # Получение осей
        right_trigger = (self.joystick.get_axis(5) + 1) / 2
        left_trigger = (self.joystick.get_axis(2) + 1) / 2
        steering = self.joystick.get_axis(0)

        # Обработка кнопок
        button_states = {
            btn: self.joystick.get_button(btn)
            for btn in self.button_actions.keys()
        }

        self._handle_buttons(button_states)

        return {
            'speed': right_trigger,
            'brake': left_trigger,
            'steering': steering
        }

    def _handle_buttons(self, button_states):
        for btn, state in button_states.items():
            if state and btn in self.button_actions:
                self.button_actions[btn]()

    def run(self):
        while True:
            gamepad_input = self.process_gamepad_input()
            if gamepad_input:
                self.input_queue.put(gamepad_input)