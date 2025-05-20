class Speed:
    def __init__(self, min_val, max_val):
        self.min_val = min_val
        self.max_val = max_val

    def scale_gas(self, value, default_value):
        """Масштабирует значение газа от 0 до 1 в диапазон [default_value, max_val]."""
        return int(default_value + abs(default_value - self.max_val) * value)

    def scale_brake(self, value, default_value):
        """Масштабирует значение тормоза от 0 до 1 в диапазон [min_val, default_value]."""
        return int(default_value - abs(default_value - self.min_val) * value)
