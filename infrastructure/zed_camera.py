import cv2
import time
import os
import numpy as np
import pyzed.sl as sl
import logging
from core.interfaces.input_device import InputDevice
from core.interfaces.video_recorder import VideoRecorder
from core.entities.command import CarCommand

logger = logging.getLogger(__name__)

class ZEDCameraInput(InputDevice):
    def __init__(self, video_recorder: VideoRecorder):
        self.zed = None
        self.video_recorder = video_recorder
        self.window_name = "ZED Camera Feed"
        self.show_window = False
        self.window_created = False
        self.brake_duration = 0.5
        self.braking = False
        self.brake_start_time = None

    def initialize(self) -> None:
        self.zed = sl.Camera()
        init_params = sl.InitParameters()
        init_params.camera_resolution = sl.RESOLUTION.HD720
        init_params.camera_fps = 30
        init_params.depth_mode = sl.DEPTH_MODE.PERFORMANCE
        init_params.coordinate_units = sl.UNIT.METER
        init_params.sdk_verbose = 1
        if self.zed.open(init_params) != sl.ERROR_CODE.SUCCESS:
            logger.error("Failed to initialize ZED camera")
            raise RuntimeError("ZED camera initialization failed")
        self.video_recorder.initialize()
        logger.info("ZED camera initialized")

    def get_input(self) -> CarCommand:
        if not self.zed or not self.zed.is_opened():
            logger.error("ZED camera not initialized")
            return CarCommand(speed=0.0, brake=0.0, steering=0.0)

        image_zed = sl.Mat()
        depth_zed = sl.Mat()
        if self.zed.grab(sl.RuntimeParameters()) != sl.ERROR_CODE.SUCCESS:
            logger.error("Failed to grab ZED frame")
            return CarCommand(speed=0.0, brake=0.0, steering=0.0)

        self.zed.retrieve_image(image_zed, sl.VIEW.LEFT)
        self.zed.retrieve_measure(depth_zed, sl.MEASURE.DEPTH)
        frame = image_zed.get_data()[:, :, :3]
        depth_data = depth_zed.get_data()

        if self.video_recorder.recording:
            self.video_recorder.record_frame(frame)

        if self.show_window and self.window_created:
            depth_display = cv2.normalize(depth_data, None, 0, 255, cv2.NORM_MINMAX, cv2.CV_8U)
            cv2.imshow(self.window_name, frame)
            cv2.imshow("Depth Map", depth_display)
            cv2.waitKey(1)

        speed, brake, steering = self.process_frame(frame, depth_data)
        return CarCommand(speed=speed, brake=brake, steering=steering)

    def process_frame(self, frame, depth_data):
        height, width = depth_data.shape
        roi_height, roi_width = int(height * 0.2), int(width * 0.2)
        center_y, center_x = height // 2, width // 2
        roi = depth_data[center_y - roi_height // 2:center_y + roi_height // 2,
                         center_x - roi_width // 2:center_x + roi_width // 2]

        valid_depth = roi[np.isfinite(roi) & (roi > 0)]
        min_distance = np.min(valid_depth) if valid_depth.size > 0 else float('inf')

        current_time = time.time()
        depth_threshold = 0.6  # TODO: Get from state_manager
        if min_distance < depth_threshold:
            if not self.braking:
                self.braking = True
                self.brake_start_time = current_time
                logger.debug("Braking started")
            if self.brake_start_time and (current_time - self.brake_start_time) < self.brake_duration:
                speed, brake = 0.0, 0.0
            else:
                speed, brake = 0.0, 0.0
        else:
            self.braking = False
            self.brake_start_time = None
            speed, brake = 0.7, 0.0

        return speed, brake, 0.0

    def close(self) -> None:
        if self.zed:
            self.zed.close()
        if self.window_created:
            cv2.destroyAllWindows()
        self.video_recorder.close()
        logger.info("ZED camera closed")