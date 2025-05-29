from abc import ABC, abstractmethod
from ...core.communication.message_types import ArduinoCommand

class BaseOutput(ABC):
    @abstractmethod
    def initialize(self) -> None:
        pass

    @abstractmethod
    def send_command(self, command: ArduinoCommand) -> None:
        pass

    @abstractmethod
    def close(self) -> None:
        pass