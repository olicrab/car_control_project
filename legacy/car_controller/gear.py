from enum import Enum
from typing import Tuple

class GearDirection(Enum):
    FORWARD = "forward"
    REVERSE = "reverse"

class Gear:
    def __init__(self, max_speed: int, direction: GearDirection):
        self.max_speed = max_speed  # Максимальная скорость (0–100)
        self.direction = direction  # Направление: вперед или назад

    def scale_speed(self, value: float, neutral_value: int = 90) -> int:
        """Масштабирует значение скорости (0–1) в диапазон Arduino."""
        if value < 0 or value > 1:
            raise ValueError("Скорость должна быть от 0 до 1")

        scaled_speed = int(value * self.max_speed)  # Масштабируем до max_speed

        if self.direction == GearDirection.FORWARD:
            # Для движения вперед: 90 (нейтраль) → 180 (макс. скорость)
            return neutral_value + (scaled_speed * (180 - neutral_value) // 100)
        else:
            # Для движения назад: 90 (нейтраль) → 0 (макс. скорость)
            return neutral_value - (scaled_speed * neutral_value // 100)