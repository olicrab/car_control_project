from abc import ABC, abstractmethod

class ArduinoInterface(ABC):
    @abstractmethod
    def send_command(self, motor_value: int, steering_value: int) -> None:
        pass

    @abstractmethod
    def initialize(self) -> None:
        pass

    @abstractmethod
    def close(self) -> None:
        pass