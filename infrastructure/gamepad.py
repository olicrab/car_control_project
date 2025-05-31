import pygame
import logging
from core.interfaces.input_device import InputDevice
from core.entities.command import CarCommand
from .button_handler import GamepadButtonHandler
from application.state_manager import StateManager

logger = logging.getLogger(__name__)

class GamepadInput(InputDevice):
    def __init__(self, joystick_index: int, state_manager: StateManager):
        self.joystick_index = joystick_index
        self.state_manager = state_manager
        self.joystick = None
        self.button_handler = GamepadButtonHandler()
        self.steering_trim = 0.0
        self.trim_step = 2.0 / 90
        self.prev_dpad = (0, 0)
        self.rumble_supported = False
        logger.info("GamepadInput initialized")

    def initialize(self) -> None:
        pygame.init()
        pygame.joystick.init()
        joystick_count = pygame.joystick.get_count()
        logger.info(f"Found {joystick_count} joystick(s)")
        if joystick_count == 0:
            logger.error("No joystick detected")
            self.state_manager.update_state(last_error="No joystick detected")
            raise RuntimeError("No joystick detected")
        if self.joystick_index >= joystick_count:
            logger.error(f"Joystick index {self.joystick_index} out of range")
            self.state_manager.update_state(last_error=f"Joystick index {self.joystick_index} out of range")
            raise RuntimeError(f"Joystick index {self.joystick_index} out of range")

        self.joystick = pygame.joystick.Joystick(self.joystick_index)
        self.joystick.init()
        logger.info(f"Joystick initialized: {self.joystick.get_name()}")
        logger.info(f"Number of axes: {self.joystick.get_numaxes()}, buttons: {self.joystick.get_numbuttons()}")
        try:
            self.joystick.rumble(0.5, 0.5, 300)
            self.rumble_supported = True
            logger.info("Gamepad vibration supported")
        except pygame.error:
            logger.warning("Gamepad vibration not supported")

    def register_button_action(self, button_id: int, action) -> None:
        logger.debug(f"Registering action for button {button_id}")
        self.button_handler.register_action(button_id, action)

    def get_input(self) -> CarCommand:
        try:
            pygame.event.pump()
            axes = {i: self.joystick.get_axis(i) for i in range(self.joystick.get_numaxes())}
            logger.debug(f"Raw axes values: {axes}")

            # Альтернативные индексы для Jetson
            stick_x = axes.get(0, 0.0)  # Левый стик X
            right_trigger = (axes.get(5, -1.0) + 1) / 2 if 5 in axes else 0.0  # RT
            left_trigger = (axes.get(2, -1.0) + 1) / 2 if 2 in axes else 0.0  # LT
            dpad = self.joystick.get_hat(0)

            button_states = {i: self.joystick.get_button(i) for i in range(self.joystick.get_numbuttons())}
            logger.debug(f"Button states: {button_states}")
            self.button_handler.handle_buttons(button_states)

            right_trigger = max(0.0, min(1.0, right_trigger))
            left_trigger = max(0.0, min(1.0, left_trigger))
            stick_x = max(-1.0, min(1.0, stick_x))

            dpad_x, dpad_y = dpad
            prev_dpad_x, prev_dpad_y = self.prev_dpad
            command = CarCommand(
                speed=right_trigger,
                brake=left_trigger,
                steering=stick_x + self.steering_trim
            )

            if dpad_x == -1 and prev_dpad_x != -1:
                self.steering_trim -= self.trim_step
                command.trim = self.steering_trim
                self.state_manager.update_state(trim=self.steering_trim)
                logger.debug(f"Trim adjusted left: {self.steering_trim:.3f}")
            if dpad_x == 1 and prev_dpad_x != 1:
                self.steering_trim += self.trim_step
                command.trim = self.steering_trim
                self.state_manager.update_state(trim=self.steering_trim)
                logger.debug(f"Trim adjusted right: {self.steering_trim:.3f}")
            if dpad_y == -1 and prev_dpad_y != -1:
                current_threshold = self.state_manager.get_state().get("depth_threshold", 0.6)
                new_threshold = max(0.1, current_threshold - 0.05)
                command.depth_threshold = new_threshold
                self.state_manager.update_state(depth_threshold=new_threshold)
                logger.debug(f"Depth threshold decreased: {new_threshold:.2f}")
            if dpad_y == 1 and prev_dpad_y != 1:
                current_threshold = self.state_manager.get_state().get("depth_threshold", 0.6)
                new_threshold = current_threshold + 0.05
                command.depth_threshold = new_threshold
                self.state_manager.update_state(depth_threshold=new_threshold)
                logger.debug(f"Depth threshold increased: {new_threshold:.2f}")

            self.prev_dpad = dpad
            logger.debug(f"Gamepad state: speed={command.speed:.2f}, brake={command.brake:.2f}, steering={command.steering:.2f}")
            return command
        except Exception as e:
            logger.error(f"Gamepad input error: {e}")
            self.state_manager.update_state(last_error=f"Gamepad input error: {e}")
            return CarCommand(speed=0.0, brake=0.0, steering=0.0)

    def set_steering_trim(self, trim: float) -> None:
        self.steering_trim = trim
        self.state_manager.update_state(trim=trim)
        logger.debug(f"Trim set to: {trim:.3f}")

    def close(self) -> None:
        if self.joystick:
            self.joystick.quit()
        pygame.quit()
        logger.info("Gamepad disconnected")