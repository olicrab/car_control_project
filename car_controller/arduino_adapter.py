from typing import Dict, Tuple
from .gear import Gear, GearDirection

class ArduinoAdapter:
    def __init__(self, gears: Dict[str, Gear], default_gear: str = "medium"):
        self.gears = gears
        self.current_gear = default_gear
        self.neutral_motor_value = 90  # Нейтральное значение мотора

    def set_gear(self, gear_name: str) -> None:
        """Устанавливает текущую передачу."""
        if gear_name in self.gears:
            self.current_gear = gear_name
            print(f"Передача установлена: {gear_name}")
        else:
            print(f"Неизвестная передача: {gear_name}. Остаётся {self.current_gear}")

    def increase_gear(self) -> None:
        """Переключает на следующую передачу."""
        gear_names = list(self.gears.keys())
        current_index = gear_names.index(self.current_gear)
        if current_index < len(gear_names) - 1:
            self.current_gear = gear_names[current_index + 1]
            print(f"Передача увеличена: {self.current_gear}")
        else:
            print("Вы на максимальной передаче!")

    def decrease_gear(self) -> None:
        """Переключает на предыдущую передачу."""
        gear_names = list(self.gears.keys())
        current_index = gear_names.index(self.current_gear)
        if current_index > 0:
            self.current_gear = gear_names[current_index - 1]
            print(f"Передача уменьшена: {self.current_gear}")
        else:
            print("Вы на минимальной передаче!")

    def convert_commands(self, speed: float, steering: float) -> Tuple[int, int]:
        """Преобразует команды скорости и руления в значения для Arduino."""
        gear = self.gears[self.current_gear]
        motor_value = gear.scale_speed(speed, self.neutral_motor_value)
        # Руль: -0.5 (влево) → 180, 0.0 (прямо) → 90, 0.5 (вправо) → 0
        steering_value = int(90 - (steering * 90))
        steering_value = max(0, min(180, steering_value))  # Ограничиваем 0–180
        return motor_value, steering_value