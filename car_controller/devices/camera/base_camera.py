from abc import ABC, abstractmethod
import numpy as np
from typing import Tuple, Optional

class BaseCamera(ABC):
    @abstractmethod
    def initialize(self) -> None:
        pass

    @abstractmethod
    def get_frame(self) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """Returns (image, depth)"""
        pass

    @abstractmethod
    def close(self) -> None:
        pass