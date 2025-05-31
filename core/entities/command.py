from dataclasses import dataclass
from typing import Optional

@dataclass
class CarCommand:
    speed: float
    brake: float
    steering: float
    gear: Optional[str] = None
    record: Optional[bool] = None
    mode: Optional[str] = None
    trim: Optional[float] = None
    depth_threshold: Optional[float] = None