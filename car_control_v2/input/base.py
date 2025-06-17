from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Tuple, Optional
import logging

@dataclass
class InputState:
    """Состояние устройства ввода."""
    speed: float = 0.0
    brake: float = 0.0
    steering: float = 0.0
    is_recording: bool = False
    error: Optional[str] = None

class InputDevice(ABC):
    """Базовый класс для устройств ввода."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self._state = InputState()
        self._is_initialized = False
        self._is_running = False

    @property
    def state(self) -> InputState:
        """Возвращает текущее состояние устройства."""
        return self._state

    @property
    def is_initialized(self) -> bool:
        """Проверяет, инициализировано ли устройство."""
        return self._is_initialized

    @property
    def is_running(self) -> bool:
        """Проверяет, работает ли устройство."""
        return self._is_running

    @abstractmethod
    def initialize(self) -> None:
        """Инициализирует устройство."""
        pass

    @abstractmethod
    def start(self) -> None:
        """Запускает устройство."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Останавливает устройство."""
        pass

    @abstractmethod
    def update(self) -> None:
        """Обновляет состояние устройства."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Закрывает устройство и освобождает ресурсы."""
        pass

    def _set_error(self, error: str) -> None:
        """Устанавливает ошибку в состоянии."""
        self._state.error = error
        self.logger.error(error)

    def _clear_error(self) -> None:
        """Очищает ошибку в состоянии."""
        self._state.error = None 