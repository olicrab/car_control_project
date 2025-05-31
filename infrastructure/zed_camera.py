import cv2
import time
import os
import numpy as np
import pyzed.sl as sl
import logging
from core.interfaces.input_device import InputDevice
from core.interfaces.video_recorder import VideoRecorder
from core.entities.command import CarCommand
from application.state_manager import StateManager

logger = logging.getLogger(__name__)

class ZEDCameraInput(InputDevice):
    def __init__(self, video_recorder: VideoRecorder, state_manager: StateManager):
        self.zed = None
        self.video_recorder = video_recorder
        self.state_manager = state_manager
        self.window_name = "ZED Camera Feed"
        self.show_window = False
        self.window_created = False
        self.brake_duration = 0.5
        self.braking = False
        self.brake_start_time = None
        self.min_distance = float('inf')
        logger.info("ZEDCameraInput initialized")

    def initialize(self) -> None:
        try:
            self.zed = sl.Camera()
            init_params = sl.InitParameters()
            init_params.camera_resolution = sl.RESOLUTION.HD720
            init_params.camera_fps = 30
            init_params.depth_mode = sl.DEPTH_MODE.PERFORMANCE
            init_params.coordinate_units = sl.UNIT.METER
            init_params.sdk_verbose = 1
            init_params.depth_minimum_distance = 0.3
            init_params.depth_maximum_distance = 10.0
            status = self.zed.open(init_params)
            if status != sl.ERROR_CODE.SUCCESS:
                logger.error(f"Failed to initialize ZED camera: {status}")
                self.state_manager.update_state(last_error=f"ZED camera initialization failed: {status}")
                raise RuntimeError(f"ZED camera initialization failed: {status}")
            self.video_recorder.initialize()
            logger.info("ZED camera initialized")
        except Exception as e:
            logger.error(f"ZED initialization error: {e}")
            self.state_manager.update_state(last_error=f"ZED initialization error: {e}")
            raise

    def get_input(self) -> CarCommand:
        try:
            if not self.zed or not self.zed.is_opened():
                logger.error("ZED camera not initialized")
                self.state_manager.update_state(last_error="ZED camera not initialized")
                return CarCommand(speed=0.0, brake=0.0, steering=0.0)

            runtime_params = sl.RuntimeParameters()
            status = self.zed.grab(runtime_params)
            if status != sl.ERROR_CODE.SUCCESS:
                logger.error(f"Failed to grab ZED frame: {status}")
                self.state_manager.update_state(last_error=f"Failed to grab ZED frame: {status}")
                return CarCommand(speed=0.0, brake=0.0, steering=0.0)

            image_zed = sl.Mat()
            depth_zed = sl.Mat()
            self.zed.retrieve_image(image_zed, sl.VIEW.LEFT)
            self.zed.retrieve_measure(depth_zed, sl.MEASURE.DEPTH)
            frame = image_zed.get_data()[:, :, :3]
            depth_data = depth_zed.get_data()

            if self.video_recorder.recording:
                self.video_recorder.record_frame(frame)

            if self.show_window and not self.window_created:
                width = self.zed.get_camera_information().camera_configuration.resolution.width
                height = self.zed.get_camera_information().camera_configuration.resolution.height
                cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
                cv2.namedWindow("Depth Map", cv2.WINDOW_NORMAL)
                cv2.resizeWindow(self.window_name, width // 2, height // 2)
                cv2.resizeWindow("Depth Map", width // 2, height // 2)
                self.window_created = True
                logger.debug("ZED camera windows created")

            if self.show_window and self.window_created:
                logger.debug(f"Depth data stats: min={np.nanmin(depth_data):.2f}, max={np.nanmax(depth_data):.2f}, mean={np.nanmean(depth_data):.2f}, nan_count={np.isnan(depth_data).sum()}, inf_count={np.isinf(depth_data).sum()}")
                depth_display = depth_data.copy()
                depth_display[np.isinf(depth_display) | np.isnan(depth_display)] = 10.0  # Заменяем inf/nan
                depth_display = np.clip(depth_display, 0, 10)  # Ограничиваем
                depth_display = cv2.normalize(depth_display, None, 0, 255, cv2.NORM_MINMAX, cv2.CV_8U)
                depth_display = cv2.applyColorMap(depth_display, cv2.COLORMAP_JET)
                cv2.imshow(self.window_name, cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))  # Конвертация RGB в BGR
                cv2.imshow("Depth Map", depth_display)
                cv2.waitKey(1)

            speed, brake, steering = self.process_frame(frame, depth_data)
            self.state_manager.update_state(
                min_distance=self.min_distance,
                braking=self.braking,
                recording=self.video_recorder.recording
            )
            return CarCommand(speed=speed, brake=brake, steering=steering)
        except Exception as e:
            logger.error(f"ZED input error: {e}")
            self.state_manager.update_state(last_error=f"ZED input error: {e}")
            return CarCommand(speed=0.0, brake=0.0, steering=0.0)

    def process_frame(self, frame, depth_data):
        try:
            height, width = depth_data.shape
            roi_height, roi_width = int(height * 0.2), int(width * 0.2)
            center_y, center_x = height // 2, width // 2
            roi = depth_data[center_y - roi_height // 2:center_y + roi_height // 2,
                             center_x - roi_width // 2:center_x + roi_width // 2]

            valid_depth = roi[np.isfinite(roi) & (roi > 0)]
            self.min_distance = np.min(valid_depth) if valid_depth.size > 0 else float('inf')

            depth_threshold = self.state_manager.get_state().get("depth_threshold", 0.6)
            current_time = time.time()
            if self.min_distance < depth_threshold:
                if not self.braking:
                    self.braking = True
                    self.brake_start_time = current_time
                    logger.debug("Braking started")
                    self.state_manager.update_state(braking=True)
                speed, brake = 0.0, 0.0
            else:
                self.braking = False
                self.brake_start_time = None
                speed, brake = 0.7, 0.0
                self.state_manager.update_state(braking=False)

            return speed, brake, 0.0
        except Exception as e:
            logger.error(f"ZED frame processing error: {e}")
            self.state_manager.update_state(last_error=f"ZED frame processing error: {e}")
            return 0.0, 0.0, 0.0

    def set_window_visible(self, visible: bool) -> None:
        self.show_window = visible
        if not visible and self.window_created:
            try:
                cv2.destroyWindow(self.window_name)
                cv2.destroyWindow("Depth Map")
                self.window_created = False
                logger.debug("ZED camera windows closed")
            except cv2.error as e:
                logger.error(f"Error closing ZED windows: {e}")
                self.state_manager.update_state(last_error=f"Error closing ZED windows: {e}")

    def close(self) -> None:
        try:
            if self.zed:
                self.zed.close()
            if self.window_created:
                try:
                    cv2.destroyAllWindows()
                    self.window_created = False
                except cv2.error as e:
                    logger.error(f"Error closing ZED windows: {e}")
            self.video_recorder.close()
            logger.info("ZED camera closed")
        except Exception as e:
            logger.error(f"ZED close error: {e}")
            self.state_manager.update_state(last_error=f"ZED close error: {e}")