from dataclasses import dataclass

@dataclass
class CarCommand:
    speed: float
    brake: float
    steering: float
    gear: str = None
    record: bool = None
    mode: str = None
    trim: float = None
    depth_threshold: float = None