from typing import Dict
from core.entities.gear import Gear, GearDirection
from core.entities.command import CarCommand
from core.interfaces.arduino_interface import ArduinoInterface
from .state_manager import StateManager

class CarController:
    def __init__(self, arduino: ArduinoInterface, state_manager: StateManager):
        self.arduino = arduino
        self.state_manager = state_manager
        self.gears: Dict[str, Gear] = {
            "turtle": Gear(max_speed=15, direction=GearDirection.FORWARD),
            "slow": Gear(max_speed=30, direction=GearDirection.FORWARD),
            "medium": Gear(max_speed=50, direction=GearDirection.FORWARD),
            "fast": Gear(max_speed=100, direction=GearDirection.FORWARD),
            "reverse": Gear(max_speed=30, direction=GearDirection.REVERSE)
        }
        self.neutral_motor_value = 90

    def process_command(self, command: CarCommand) -> None:
        if command.gear:
            self.state_manager.update_state(gear=command.gear)
        if command.trim is not None:
            self.state_manager.update_state(trim=command.trim)
        if command.depth_threshold is not None:
            self.state_manager.update_state(depth_threshold=command.depth_threshold)

        gear = self.gears[self.state_manager.get_state().get("gear", "turtle")]
        if command.brake > 0.0:
            brake_direction = GearDirection.REVERSE if gear.direction == GearDirection.FORWARD else GearDirection.FORWARD
            brake_gear = Gear(gear.max_speed, brake_direction)
            motor_value = brake_gear.scale_speed(command.brake, self.neutral_motor_value)
        else:
            motor_value = gear.scale_speed(command.speed, self.neutral_motor_value)

        steering_value = int(90 - (command.steering * 90))
        steering_value = max(0, min(180, steering_value))
        self.arduino.send_command(motor_value, steering_value)