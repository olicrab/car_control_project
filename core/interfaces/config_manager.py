from abc import ABC, abstractmethod
from typing import Dict

class ConfigManager(ABC):
    @abstractmethod
    def get_config(self) -> Dict:
        pass

    @abstractmethod
    def update_config(self, key: str, value) -> None:
        pass