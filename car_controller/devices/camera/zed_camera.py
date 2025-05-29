from typing import Tuple, Optional

import pyzed.sl as sl
import numpy as np
from .base_camera import BaseCamera
from .camera_exceptions import CameraInitializationError


class ZEDCamera(BaseCamera):
    def __init__(self):
        self.zed = sl.Camera()
        self.init_params = sl.InitParameters()
        self.init_params.depth_mode = sl.DEPTH_MODE.PERFORMANCE
        self.init_params.coordinate_units = sl.UNIT.METER
        self.runtime_params = sl.RuntimeParameters()

    def initialize(self) -> None:
        err = self.zed.open(self.init_params)
        if err != sl.ERROR_CODE.SUCCESS:
            raise CameraInitializationError(f"Failed to open ZED camera: {err}")

    def get_frame(self) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:  # Исправляем типы
        if self.zed.grab(self.runtime_params) != sl.ERROR_CODE.SUCCESS:
            return None, None

        image = sl.Mat()
        depth = sl.Mat()
        self.zed.retrieve_image(image, sl.VIEW.LEFT)
        self.zed.retrieve_measure(depth, sl.MEASURE.DEPTH)
        return image.get_data(), depth.get_data()

    def close(self) -> None:
        self.zed.close()