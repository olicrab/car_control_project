from enum import Enum
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

class GearDirection(Enum):
    FORWARD = "forward"
    REVERSE = "reverse"

@dataclass
class Gear:
    max_speed: int  # 0–100
    direction: GearDirection

    def scale_speed(self, value: float, neutral_value: int = 90) -> int:
        if not 0 <= value <= 1:
            logger.error(f"Invalid speed value: {value}, must be between 0 and 1")
            raise ValueError("Speed must be between 0 and 1")
        scaled_speed = int(value * self.max_speed)
        if self.direction == GearDirection.FORWARD:
            return neutral_value + (scaled_speed * (180 - neutral_value) // 100)
        return neutral_value - (scaled_speed * neutral_value // 100)