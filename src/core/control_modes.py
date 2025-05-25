from enum import Enum, auto

class ControlMode(Enum):
    MANUAL = auto()
    AUTOPILOT = auto()
    EMERGENCY_STOP = auto()

class ControlStrategy:
    def process_input(self, input_data):
        raise NotImplementedError("Subclasses must implement this method")

class ManualControlStrategy(ControlStrategy):
    def process_input(self, input_data):
        # Логика ручного управления
        return input_data

class AutopilotControlStrategy(ControlStrategy):
    def __init__(self, camera_processor):
        self.camera_processor = camera_processor

    def process_input(self, input_data):
        # Логика автопилота с использованием данных камеры
        return self.camera_processor.get_control_commands()