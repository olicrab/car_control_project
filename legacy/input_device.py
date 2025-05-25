from abc import ABC, abstractmethod
from typing import Tuple

class InputDevice(ABC):
    @abstractmethod
    def get_input(self) -> Tuple[float, float, float, bool, bool]:
        """Возвращает значения газа, тормоза, поворота и состояния бамперов."""
        pass

    @abstractmethod
    def initialize(self) -> None:
        """Инициализирует устройство ввода."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Закрывает устройство ввода."""
        pass