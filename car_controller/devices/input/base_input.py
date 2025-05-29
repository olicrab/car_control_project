from abc import ABC, abstractmethod
from typing import Tuple

class BaseInput(ABC):
    @abstractmethod
    def initialize(self) -> None:
        pass

    @abstractmethod
    def get_input(self) -> Tuple[float, float, float, bool, bool]:
        """Returns (speed, brake, steering, emergency_stop, recording)"""
        pass

    @abstractmethod
    def close(self) -> None:
        pass