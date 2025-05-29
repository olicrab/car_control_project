from dataclasses import dataclass
from typing import Optional
import numpy as np

@dataclass
class CameraFrame:
    image: np.ndarray
    depth: Optional[np.ndarray] = None
    timestamp: float = 0.0

@dataclass
class ControlCommand:
    speed: float
    brake: float
    steering: float
    timestamp: float

@dataclass
class ArduinoCommand:
    motor_value: int      # 0-180
    steering_value: int   # 45-135
    timestamp: float