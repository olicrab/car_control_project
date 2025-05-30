import pygame
import logging
from core.interfaces.input_device import InputDevice
from core.entities.command import CarCommand
from .button_handler import GamepadButtonHandler

logger = logging.getLogger(__name__)

class GamepadInput(InputDevice):
    def __init__(self, joystick_index: int = 0):
        self.joystick_index = joystick_index
        self.joystick = None
        self.button_handler = GamepadButtonHandler()
        self.steering_trim = 0.0
        self.trim_step = 2.0 / 90
        self.prev_dpad = (0, 0)
        self.rumble_supported = False

    def initialize(self) -> None:
        pygame.init()
        self.joystick = pygame.joystick.Joystick(self.joystick_index)
        self.joystick.init()
        try:
            self.joystick.rumble(0.5, 0.5, 300)
            self.rumble_supported = True
            logger.info("Gamepad vibration supported")
        except pygame.error:
            logger.warning("Gamepad vibration not supported")
        logger.info("Gamepad initialized")

    def register_button_action(self, button_id: int, action) -> None:
        self.button_handler.register_action(button_id, action)

    def get_input(self) -> CarCommand:
        pygame.event.pump()
        right_trigger = (self.joystick.get_axis(5) + 1) / 2
        left_trigger = (self.joystick.get_axis(2) + 1) / 2
        stick_x = self.joystick.get_axis(0)
        dpad = self.joystick.get_hat(0)

        button_states = {i: self.joystick.get_button(i) for i in range(8)}
        self.button_handler.handle_buttons(button_states)

        dpad_x, dpad_y = dpad
        prev_dpad_x, prev_dpad_y = self.prev_dpad
        command = CarCommand(speed=right_trigger, brake=left_trigger, steering=stick_x + self.steering_trim)

        if dpad_x == -1 and prev_dpad_x != -1:
            self.steering_trim -= self.trim_step
            command.trim = self.steering_trim
        if dpad_x == 1 and prev_dpad_x != 1:
            self.steering_trim += self.trim_step
            command.trim = self.steering_trim
        if dpad_y == -1 and prev_dpad_y != -1:
            command.depth_threshold = 0.55  # Example
        if dpad_y == 1 and prev_dpad_y != 1:
            command.depth_threshold = 0.65

        self.prev_dpad = dpad
        return command

    def close(self) -> None:
        if self.joystick:
            self.joystick.quit()
        pygame.quit()
        logger.info("Gamepad disconnected")