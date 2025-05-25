import cv2
import numpy as np
from src.utils.config import ConfigManager
from src.utils.logger import Logger


class AutopilotProcessor:
    def __init__(self):
        self.config = ConfigManager()
        self.logger = Logger()
        self.depth_threshold = 0.6

    def get_control_commands(self, frame, depth_data):
        """
        Логика автопилота с обработкой кадра и глубины
        """
        try:
            # Анализ глубины и принятие решений
            min_distance = self._calculate_min_distance(depth_data)

            if min_distance < self.depth_threshold:
                return {
                    'speed': 0.0,
                    'brake': 1.0,
                    'steering': 0.0
                }

            # Базовая логика движения вперед
            return {
                'speed': 0.5,
                'brake': 0.0,
                'steering': 0.0
            }

        except Exception as e:
            self.logger.error(f"Autopilot processing error: {e}")
            return {
                'speed': 0.0,
                'brake': 0.0,
                'steering': 0.0
            }

    def _calculate_min_distance(self, depth_data):
        # Логика вычисления минимального расстояния
        valid_depths = depth_data[np.isfinite(depth_data) & (depth_data > 0)]
        return np.min(valid_depths) if valid_depths.size > 0 else float('inf')
