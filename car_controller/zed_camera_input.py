import cv2
import time
import os
import numpy as np
import pyzed.sl as sl
import logging
import logging.handlers
from .input_device import InputDevice
from typing import Tuple, Optional
import multiprocessing as mp

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.handlers.RotatingFileHandler('car_control.log', maxBytes=5*1024*1024, backupCount=3)
    ]
)
logger = logging.getLogger(__name__)

class ZEDCameraInput(InputDevice):
    def __init__(self):
        self.zed = None
        self.window_name = "ZED Camera Feed"
        self.recording = False
        self.out = None
        self.output_dir = os.path.dirname(__file__)
        self.output_path = self._generate_output_path()
        self.show_window = False
        self.window_created = False
        self.default_depth_threshold = 0.6
        self.depth_threshold = self.default_depth_threshold
        self.depth_step = 0.05
        self.steering_trim = 0.0
        self.gamepad_input = None
        self.min_distance = float('inf')
        self.last_error = ""
        self.braking = False
        self.brake_start_time: Optional[float] = None
        self.brake_duration = 0.5
        # Positional tracking attributes
        self.tracking_enabled = False
        self.camera_pose = sl.Pose()
        self.translation = [0.0, 0.0, 0.0]  # x, y, z in meters
        self.rotation = [0.0, 0.0, 0.0]    # roll, pitch, yaw in radians
        self.tracking_state = sl.POSITIONAL_TRACKING_STATE.OFF

    def _generate_output_path(self) -> str:
        timestamp = int(time.time())
        return os.path.join(self.output_dir, f"output_{timestamp}.avi")

    def set_gamepad_input(self, gamepad_input: 'GamepadInput') -> None:
        self.gamepad_input = gamepad_input
        logger.debug("Gamepad input set for ZED camera")

    def initialize(self) -> None:
        self.close()
        self.zed = sl.Camera()
        init_params = sl.InitParameters()
        init_params.camera_resolution = sl.RESOLUTION.HD720
        init_params.camera_fps = 30
        init_params.depth_mode = sl.DEPTH_MODE.NEURAL
        init_params.coordinate_units = sl.UNIT.METER
        init_params.sdk_verbose = 1

        err = self.zed.open(init_params)
        if err != sl.ERROR_CODE.SUCCESS:
            self.last_error = f"ZED camera initialization error: {err}"
            logger.error(self.last_error)
            raise RuntimeError(self.last_error)

        # Enable positional tracking
        tracking_params = sl.PositionalTrackingParameters()
        tracking_params.enable_imu_fusion = True
        tracking_params.mode = sl.POSITIONAL_TRACKING_MODE.GEN_1
        err = self.zed.enable_positional_tracking(tracking_params)
        if err != sl.ERROR_CODE.SUCCESS:
            self.last_error = f"Positional tracking initialization error: {err}"
            logger.error(self.last_error)
            raise RuntimeError(self.last_error)
        self.tracking_enabled = True
        logger.info("Positional tracking enabled")

        camera_info = self.zed.get_camera_information()
        width = camera_info.camera_configuration.resolution.width
        height = camera_info.camera_configuration.resolution.height
        fps = camera_info.camera_configuration.fps
        logger.info(f"ZED camera initialized: {width}x{height}, {fps} FPS")

    def toggle_recording(self) -> None:
        if not self.recording:
            if not self.zed or not self.zed.is_opened():
                self.last_error = "Error: ZED camera not initialized"
                logger.error(self.last_error)
                return
            if not os.access(self.output_dir, os.W_OK):
                self.last_error = f"Error: No write permissions for {self.output_dir}"
                logger.error(self.last_error)
                return
            width = self.zed.get_camera_information().camera_configuration.resolution.width
            height = self.zed.get_camera_information().camera_configuration.resolution.height
            fps = self.zed.get_camera_information().camera_configuration.fps or 20.0
            codecs = ['XVID', 'MJPG', 'H264', 'DIVX']
            for codec in codecs:
                fourcc = cv2.VideoWriter_fourcc(*codec)
                self.out = cv2.VideoWriter(self.output_path, fourcc, fps, (width, height))
                if self.out.isOpened():
                    logger.debug(f"VideoWriter opened with codec {codec}")
                    break
                logger.warning(f"Codec {codec} failed")
            else:
                self.last_error = "Error: Failed to initialize VideoWriter"
                logger.error(self.last_error)
                self.out = None
                return
            self.recording = True
            logger.info(f"Recording started: {self.output_path}")
            if self.gamepad_input:
                self.gamepad_input.vibrate_on_record_start()
        else:
            if self.out is not None and self.out.isOpened():
                self.out.release()
                logger.debug("VideoWriter closed")
            self.out = None
            self.recording = False
            if not os.path.exists(self.output_path) or os.path.getsize(self.output_path) == 0:
                self.last_error = f"Error: Recording file empty or not created: {self.output_path}"
                logger.error(self.last_error)
            self.output_path = self._generate_output_path()
            logger.info("Recording stopped")
            if self.gamepad_input:
                self.gamepad_input.vibrate_on_record_stop()

    def increase_depth_threshold(self) -> None:
        self.depth_threshold += self.depth_step
        logger.debug(f"Depth threshold increased: {self.depth_threshold:.2f} m")

    def decrease_depth_threshold(self) -> None:
        self.depth_threshold = max(0.1, self.depth_threshold - self.depth_step)
        logger.debug(f"Depth threshold decreased: {self.depth_threshold:.2f} m")

    def reset_depth_threshold(self) -> None:
        self.depth_threshold = self.default_depth_threshold
        logger.debug(f"Depth threshold reset: {self.depth_threshold:.2f} m")

    def get_input(self) -> Tuple[float, float, float, bool, bool]:
        if not self.zed or not self.zed.is_opened():
            self.last_error = "Error: ZED camera not initialized"
            logger.error(self.last_error)
            return 0.0, 0.0, 0.0, False, False

        image_zed = sl.Mat()
        depth_zed = sl.Mat()
        runtime_params = sl.RuntimeParameters()
        if self.zed.grab(runtime_params) != sl.ERROR_CODE.SUCCESS:
            self.last_error = "Error: Failed to grab ZED frame"
            logger.error(self.last_error)
            return 0.0, 0.0, 0.0, False, False

        self.zed.retrieve_image(image_zed, sl.VIEW.LEFT)
        self.zed.retrieve_measure(depth_zed, sl.MEASURE.DEPTH)
        frame = image_zed.get_data()[:, :, :3]
        depth_data = depth_zed.get_data()

        # Update positional tracking
        if self.tracking_enabled:
            self.tracking_state = self.zed.get_position(self.camera_pose, sl.REFERENCE_FRAME.WORLD)
            if self.tracking_state == sl.POSITIONAL_TRACKING_STATE.OK:
                translation = self.camera_pose.get_translation().get()
                rotation = self.camera_pose.get_rotation_vector()
                self.translation = [round(translation[i], 2) for i in range(3)]
                self.rotation = [round(rotation[i], 2) for i in range(3)]
                logger.debug(f"Position: {self.translation}, Rotation: {self.rotation}, Tracking: {self.tracking_state}")

        if self.recording and self.out is not None and self.out.isOpened():
            self.out.write(frame)
            logger.debug(f"Frame recorded: {frame.shape}")

        if self.show_window and self.window_created:
            depth_display = depth_data.copy()
            depth_display[np.isinf(depth_display) | np.isnan(depth_display)] = 0

            valid_depth = depth_display[depth_display > 0]
            if valid_depth.size > 0:
                min_depth = np.min(valid_depth)
                max_depth = np.max(valid_depth)
                if max_depth > min_depth:
                    depth_display = np.clip(depth_display, min_depth, max_depth)
                    depth_display = (255 * (max_depth - depth_display) / (max_depth - min_depth)).astype(np.uint8)
                else:
                    depth_display = (depth_display * 0).astype(np.uint8)
            else:
                depth_display = (depth_display * 0).astype(np.uint8)

            depth_colored = cv2.applyColorMap(depth_display, cv2.COLORMAP_JET)
            cv2.imshow(self.window_name, frame)
            cv2.imshow("Depth Map", depth_colored)
            cv2.waitKey(1)

        speed, brake, steering = self.process_frame(frame, depth_data)
        steering = max(-0.5, min(0.5, steering + self.steering_trim))
        logger.debug(f"ZED input: speed={speed:.2f}, brake={brake:.2f}, steering={steering:.2f}")
        return speed, brake, steering, False, False

    def set_window_visible(self, visible: bool) -> None:
        self.show_window = visible
        if visible and self.zed and self.zed.is_opened():
            if not self.window_created:
                width = self.zed.get_camera_information().camera_configuration.resolution.width
                height = self.zed.get_camera_information().camera_configuration.resolution.height
                cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
                cv2.namedWindow("Depth Map", cv2.WINDOW_NORMAL)
                cv2.resizeWindow(self.window_name, width, height)
                cv2.resizeWindow("Depth Map", width, height)
                self.window_created = True
                logger.debug("ZED camera windows created")
        elif not visible and self.window_created:
            try:
                cv2.destroyWindow(self.window_name)
                cv2.destroyWindow("Depth Map")
                self.window_created = False
                logger.debug("ZED camera windows closed")
            except cv2.error as e:
                self.last_error = f"Error closing ZED windows: {e}"
                logger.error(self.last_error)

    def set_steering_trim(self, trim: float) -> None:
        self.steering_trim = trim
        logger.debug(f"ZED steering trim set to: {trim:.3f}")

    def process_frame(self, frame, depth_data):
        height, width = depth_data.shape
        roi_height = int(height * 0.2)
        roi_width = int(width * 0.2)
        center_y = height // 2
        center_x = width // 2
        roi = depth_data[center_y - roi_height // 2:center_y + roi_height // 2,
                         center_x - roi_width // 2:center_x + roi_width // 2]

        valid_depth = roi[np.isfinite(roi) & (roi > 0)]
        if valid_depth.size == 0:
            self.min_distance = float('inf')
            self.braking = False
            self.brake_start_time = None
            logger.debug("No valid depth data in ROI")
            return 0.0, 0.0, 0.0

        self.min_distance = np.min(valid_depth)
        steering = 0.0

        # Логика торможения
        current_time = time.time()
        if self.min_distance < self.depth_threshold:
            if not self.braking:
                self.braking = True
                self.brake_start_time = current_time
                logger.debug("Braking started due to obstacle")
            if self.brake_start_time and (current_time - self.brake_start_time) < self.brake_duration:
                # Плавное торможение: motor_value = 89
                speed = 0.0
                brake = 0.0  # Не используем задний ход
                logger.debug("Applying brake: motor_value=89")
            else:
                # Полная остановка: motor_value = 90
                speed = 0.0
                brake = 0.0
                logger.debug("Car stopped: motor_value=90")
        else:
            # Движение вперед
            self.braking = False
            self.brake_start_time = None
            speed = 0.7
            brake = 0.0
            logger.debug("Moving forward: speed=0.7")

        return speed, brake, steering

    def close(self) -> None:
        if self.recording:
            self.toggle_recording()
        if self.zed is not None:
            if self.tracking_enabled:
                self.zed.disable_positional_tracking()
                logger.info("Positional tracking disabled")
            self.zed.close()
            self.zed = None
        if self.window_created:
            try:
                cv2.destroyWindow(self.window_name)
                cv2.destroyWindow("Depth Map")
                self.window_created = False
                logger.debug("ZED camera windows closed")
            except cv2.error as e:
                self.last_error = f"Error closing ZED windows: {e}"
                logger.error(self.last_error)
        logger.info("ZED camera closed")
