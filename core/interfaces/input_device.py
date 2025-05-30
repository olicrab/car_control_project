from abc import ABC, abstractmethod
from typing import Tuple
from ..entities.command import CarCommand

class InputDevice(ABC):
    @abstractmethod
    def get_input(self) -> CarCommand:
        pass

    @abstractmethod
    def initialize(self) -> None:
        pass

    @abstractmethod
    def close(self) -> None:
        pass