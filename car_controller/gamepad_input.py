import pygame
import time
import logging
import logging.handlers
from .input_device import InputDevice
from .button_handler import GamepadButtonHandler
from typing import Tuple, Callable

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.handlers.RotatingFileHandler('car_control.log', maxBytes=5*1024*1024, backupCount=3)
    ]
)
logger = logging.getLogger(__name__)

class GamepadInput(InputDevice):
    def __init__(self, joystick_index: int = 0):
        self.joystick_index = joystick_index
        self.joystick = None
        self.button_handler = GamepadButtonHandler()
        self.steering_trim = 0.0
        self.trim_step = 2.0 / 90
        self.prev_dpad = (0, 0)
        self.camera_input = None

    def initialize(self) -> None:
        """Initializes the gamepad."""
        try:
            self.joystick = pygame.joystick.Joystick(self.joystick_index)
            self.joystick.init()
            logger.info("Gamepad initialized")
        except pygame.error as e:
            logger.error(f"Gamepad initialization error: {e}")
            raise RuntimeError(f"Gamepad initialization error: {e}")

    def register_button_action(self, button_id: int, action: Callable[[], None]) -> None:
        self.button_handler.register_action(button_id, action)

    def adjust_trim_left(self) -> None:
        self.steering_trim -= self.trim_step
        logger.debug(f"Trim adjusted left: {self.steering_trim:.3f}")

    def adjust_trim_right(self) -> None:
        self.steering_trim += self.trim_step
        logger.debug(f"Trim adjusted right: {self.steering_trim:.3f}")

    def reset_trim(self) -> None:
        self.steering_trim = 0.0
        logger.debug("Trim reset to 0.0")

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
        logger.debug(f"Gamepad input: speed={speed:.2f}, brake={brake:.2f}, steering={steering:.2f}")

        return speed, brake, steering, False, False

    def set_steering_trim(self, trim: float) -> None:
        self.steering_trim = trim
        logger.debug(f"Trim set to: {trim:.3f}")

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
        logger.debug("Camera input set for gamepad")

    def close(self) -> None:
        if self.joystick:
            self.joystick.quit()
            self.joystick = None
        logger.info("Gamepad disconnected")