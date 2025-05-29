from typing import Optional, Tuple

import numpy as np

from ...core.logging import setup_logger
from ...core.config.settings import Settings
from .base_processor import BaseProcessor


class DepthProcessor(BaseProcessor):
    def __init__(self, settings: Settings):
        self.depth_threshold = settings.camera.depth_threshold
        self.depth_step = settings.camera.depth_step
        self.logger = setup_logger(__name__)

    def process(self, image: np.ndarray, depth: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        try:
            # Обработка изображения и карты глубины
            processed_image = image.copy()  # Здесь ваша логика обработки изображения
            processed_depth = np.clip(depth, 0, self.depth_threshold)  # Ограничение глубины
            return processed_image, processed_depth
        except Exception as e:
            self.logger.error(f"Error in depth processing: {e}")
            return image, depth  # Возвращаем исходные данные в случае ошибки