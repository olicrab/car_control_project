from abc import ABC, abstractmethod
import numpy as np
from typing import Tuple, Optional

class BaseProcessor(ABC):
    @abstractmethod
    def process(self, image: np.ndarray, depth: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        pass