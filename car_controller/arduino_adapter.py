import logging
import logging.handlers
from typing import Dict, Tuple
from .gear import Gear, GearDirection

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.handlers.RotatingFileHandler('car_control.log', maxBytes=5*1024*1024, backupCount=3)
    ]
)
logger = logging.getLogger(__name__)

class ArduinoAdapter:
    def __init__(self, gears: Dict[str, Gear], default_gear: str = "turtle"):
        self.gears = gears
        self.current_gear = default_gear
        self.neutral_motor_value = 90
        logger.debug(f"Arduino adapter initialized with default gear: {default_gear}")

    def set_gear(self, gear_name: str) -> None:
        if gear_name in self.gears:
            self.current_gear = gear_name
            logger.debug(f"Gear set to: {gear_name}")
        else:
            logger.error(f"Unknown gear: {gear_name}")

    def increase_gear(self) -> None:
        gear_names = list(self.gears.keys())
        current_index = gear_names.index(self.current_gear)
        if current_index < len(gear_names) - 1:
            self.current_gear = gear_names[current_index + 1]
            logger.debug(f"Gear increased to: {self.current_gear}")
        else:
            logger.debug("Already at maximum gear")

    def decrease_gear(self) -> None:
        gear_names = list(self.gears.keys())
        current_index = gear_names.index(self.current_gear)
        if current_index > 0:
            self.current_gear = gear_names[current_index - 1]
            logger.debug(f"Gear decreased to: {self.current_gear}")
        else:
            logger.debug("Already at minimum gear")

    def convert_commands(self, speed: float, brake: float, steering: float) -> Tuple[int, int]:
        gear = self.gears[self.current_gear]
        if brake > 0.0:
            brake_direction = (
                GearDirection.REVERSE
                if gear.direction == GearDirection.FORWARD
                else GearDirection.FORWARD
            )
            brake_gear = Gear(gear.max_speed, brake_direction)
            motor_value = brake_gear.scale_speed(brake, self.neutral_motor_value)
        else:
            motor_value = gear.scale_speed(speed, self.neutral_motor_value)

        steering_value = int(90 - (steering * 90))
        steering_value = max(0, min(180, steering_value))
        motor_value = max(80, min(105, motor_value))
        logger.debug(f"Converted commands: motor={motor_value}, steering={steering_value}")
        return motor_value, steering_value