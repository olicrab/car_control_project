class Speed:
    def __init__(self, min_val: int, max_val: int):
        self.min_val = min_val
        self.max_val = max_val

    def scale_gas(self, value: float, default_value: int) -> int:
        """Масштабирует значение газа от 0 до 1 в диапазон [default_value, max_val]."""
        return int(default_value + abs(default_value - self.max_val) * value)

    def scale_brake(self, value: float, default_value: int) -> int:
        """Масштабирует значение тормоза от 0 до 1 в диапазон [min_val, default_value]."""
        return int(default_value - abs(default_value - self.min_val) * value)