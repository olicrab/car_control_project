from typing import Dict
from core.interfaces.input_device import InputDevice
from core.entities.command import CarCommand
from .state_manager import StateManager
import logging

logger = logging.getLogger(__name__)

class InputManager:
    def __init__(self, state_manager: StateManager):
        self.devices: Dict[str, InputDevice] = {}
        self.current_mode = "gamepad"  # По умолчанию режим геймпада
        self.state_manager = state_manager
        logger.info(f"InputManager initialized with mode: {self.current_mode}")

    def register_device(self, mode: str, device: InputDevice) -> None:
        self.devices[mode] = device
        logger.info(f"Device registered: {mode}")

    def get_command(self) -> CarCommand:
        logger.debug(f"Getting command for mode: {self.current_mode}")
        device = self.devices.get(self.current_mode)
        if device:
            try:
                command = device.get_input()
                self.state_manager.update_state(
                    gear=command.gear,
                    mode=command.mode,
                    trim=command.trim,
                    depth_threshold=command.depth_threshold,
                    recording=command.record
                )
                logger.debug(f"Command received: speed={command.speed:.2f}, brake={command.brake:.2f}, steering={command.steering:.2f}")
                return command
            except Exception as e:
                logger.error(f"Error getting input from {self.current_mode}: {e}")
                self.state_manager.update_state(last_error=f"Input error: {e}")
                return CarCommand(speed=0.0, brake=0.0, steering=0.0)
        logger.warning(f"No device for mode: {self.current_mode}")
        self.state_manager.update_state(last_error=f"No device for mode: {self.current_mode}")
        return CarCommand(speed=0.0, brake=0.0, steering=0.0)

    def toggle_mode(self) -> None:
        self.current_mode = "zed" if self.current_mode == "gamepad" else "gamepad"
        self.state_manager.update_state(mode=self.current_mode)
        logger.info(f"Mode switched to: {self.current_mode}")

    def initialize(self) -> None:
        for mode, device in self.devices.items():
            try:
                device.initialize()
                logger.info(f"Device initialized: {mode}")
            except Exception as e:
                logger.error(f"Failed to initialize device {mode}: {e}")
                self.state_manager.update_state(last_error=f"Failed to initialize {mode}: {e}")

    def close(self) -> None:
        for mode, device in self.devices.items():
            try:
                device.close()
                logger.info(f"Device closed: {mode}")
            except Exception as e:
                logger.error(f"Failed to close device {mode}: {e}")