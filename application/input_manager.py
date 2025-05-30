from typing import Dict
from core.interfaces.input_device import InputDevice
from core.entities.command import CarCommand
from .state_manager import StateManager

class InputManager:
    def __init__(self, state_manager: StateManager):
        self.devices: Dict[str, InputDevice] = {}
        self.current_mode = "gamepad"
        self.state_manager = state_manager

    def register_device(self, mode: str, device: InputDevice) -> None:
        self.devices[mode] = device

    def get_command(self) -> CarCommand:
        device = self.devices.get(self.current_mode)
        if device:
            command = device.get_input()
            self.state_manager.update_state(
                gear=command.gear,
                mode=command.mode,
                trim=command.trim,
                depth_threshold=command.depth_threshold,
                recording=command.record
            )
            return command
        return CarCommand(speed=0.0, brake=0.0, steering=0.0)

    def toggle_mode(self) -> None:
        self.current_mode = "zed" if self.current_mode == "gamepad" else "gamepad"
        self.state_manager.update_state(mode=self.current_mode)