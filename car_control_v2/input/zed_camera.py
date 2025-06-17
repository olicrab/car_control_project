import cv2
import time
import os
import numpy as np
import pyzed.sl as sl
import logging
from typing import Optional, Tuple
from car_control_v2.input.base import InputDevice, InputState
from car_control_v2.config import CameraConfig

class ZEDCameraInput(InputDevice):
    """Класс для управления камерой ZED."""

    def __init__(self, config: CameraConfig, logger: Optional[logging.Logger] = None):
        super().__init__(logger)
        self.config = config
        self.zed: Optional[sl.Camera] = None
        self.window_name = "ZED Camera Feed"
        self.depth_window_name = "Depth Map"
        self.out: Optional[cv2.VideoWriter] = None
        self.output_path = self._generate_output_path()
        self.show_window = False
        self.window_created = False
        self.depth_threshold = config.depth_threshold
        self.steering_trim = 0.0
        self.min_distance = float('inf')
        self.braking = False
        self.brake_start_time: Optional[float] = None
        self.brake_duration = 0.5
        self._last_update_time = 0.0
        self._update_interval = 1.0 / config.fps

    def _generate_output_path(self) -> str:
        """Генерирует путь для сохранения видео."""
        timestamp = int(time.time())
        return os.path.join(self.config.output_dir, f"zed_output_{timestamp}.avi")

    def initialize(self) -> None:
        """Инициализирует камеру ZED."""
        try:
            self.close()
            self.zed = sl.Camera()
            
            init_params = sl.InitParameters()
            init_params.camera_resolution = sl.RESOLUTION.HD720
            init_params.camera_fps = self.config.fps
            init_params.depth_mode = getattr(sl.DEPTH_MODE, self.config.depth_mode)
            init_params.coordinate_units = sl.UNIT.METER
            init_params.sdk_verbose = True

            if self.zed is None:
                raise RuntimeError("Failed to create ZED camera instance")

            err = self.zed.open(init_params)
            if err != sl.ERROR_CODE.SUCCESS:
                raise RuntimeError(f"Failed to open ZED camera: {err}")

            camera_info = self.zed.get_camera_information()
            width = camera_info.camera_configuration.resolution.width
            height = camera_info.camera_configuration.resolution.height
            fps = camera_info.camera_configuration.fps

            self._is_initialized = True
            self.logger.info(f"ZED camera initialized: {width}x{height}, {fps} FPS")
            self._clear_error()

        except Exception as e:
            self._set_error(f"Failed to initialize ZED camera: {e}")
            raise

    def start(self) -> None:
        """Запускает обработку ввода с камеры."""
        if not self._is_initialized:
            raise RuntimeError("ZED camera not initialized")
        self._is_running = True
        self.logger.info("ZED camera input started")

    def stop(self) -> None:
        """Останавливает обработку ввода с камеры."""
        self._is_running = False
        self.logger.info("ZED camera input stopped")

    def update(self) -> None:
        """Обновляет состояние камеры."""
        if not self._is_running or not self._is_initialized or self.zed is None:
            return

        current_time = time.time()
        if current_time - self._last_update_time < self._update_interval:
            return

        try:
            image_zed = sl.Mat()
            depth_zed = sl.Mat()
            runtime_params = sl.RuntimeParameters()

            if self.zed.grab(runtime_params) != sl.ERROR_CODE.SUCCESS:
                raise RuntimeError("Failed to grab ZED frame")

            self.zed.retrieve_image(image_zed, sl.VIEW.LEFT)
            self.zed.retrieve_measure(depth_zed, sl.MEASURE.DEPTH)
            
            frame = image_zed.get_data()[:, :, :3]
            depth_data = depth_zed.get_data()

            # Запись видео
            if self._state.is_recording and self.out is not None and self.out.isOpened():
                self.out.write(frame)

            # Отображение окон
            if self.show_window and self.window_created:
                depth_display = depth_data.copy()
                depth_display[np.isinf(depth_display)] = 0
                depth_display = cv2.normalize(depth_display, None, 0, 255, cv2.NORM_MINMAX, cv2.CV_8U)
                cv2.imshow(self.window_name, frame)
                cv2.imshow(self.depth_window_name, depth_display)
                cv2.waitKey(1)

            # Обработка кадра
            speed, brake, steering = self._process_frame(frame, depth_data)
            steering = max(-0.5, min(0.5, steering + self.steering_trim))

            # Обновляем состояние
            self._state.speed = speed
            self._state.brake = brake
            self._state.steering = steering
            self._clear_error()

            self._last_update_time = current_time

        except Exception as e:
            self._set_error(f"Error updating ZED camera state: {e}")

    def _process_frame(self, frame: np.ndarray, depth_data: np.ndarray) -> Tuple[float, float, float]:
        """Обрабатывает кадр для получения команд управления."""
        height, width = depth_data.shape
        roi_height = int(height * self.config.roi_size)
        roi_width = int(width * self.config.roi_size)
        center_y = height // 2
        center_x = width // 2
        
        roi = depth_data[center_y - roi_height // 2:center_y + roi_height // 2,
                        center_x - roi_width // 2:center_x + roi_width // 2]

        valid_depth = roi[np.isfinite(roi) & (roi > 0)]
        if valid_depth.size == 0:
            self.min_distance = float('inf')
            self.braking = False
            self.brake_start_time = None
            return 0.0, 0.0, 0.0

        self.min_distance = np.min(valid_depth)
        steering = 0.0

        # Логика торможения
        current_time = time.time()
        if self.min_distance < self.depth_threshold:
            if not self.braking:
                self.braking = True
                self.brake_start_time = current_time
                self.logger.debug("Braking started due to obstacle")
            
            if self.brake_start_time and (current_time - self.brake_start_time) < self.brake_duration:
                speed = 0.0
                brake = 0.0
                self.logger.debug("Applying brake")
            else:
                speed = 0.0
                brake = 0.0
                self.logger.debug("Car stopped")
        else:
            self.braking = False
            self.brake_start_time = None
            speed = self.config.default_speed
            brake = 0.0
            self.logger.debug("Moving forward")

        return speed, brake, steering

    def toggle_recording(self) -> None:
        """Включает/выключает запись видео."""
        if not self._state.is_recording:
            if not self._is_initialized or self.zed is None:
                self._set_error("ZED camera not initialized")
                return

            if not os.access(self.config.output_dir, os.W_OK):
                self._set_error(f"No write permissions for {self.config.output_dir}")
                return

            camera_info = self.zed.get_camera_information()
            width = camera_info.camera_configuration.resolution.width
            height = camera_info.camera_configuration.resolution.height
            fps = camera_info.camera_configuration.fps or 20.0

            codecs = ['XVID', 'MJPG', 'H264', 'DIVX']
            for codec in codecs:
                fourcc = cv2.VideoWriter_fourcc(*codec)
                self.out = cv2.VideoWriter(self.output_path, fourcc, fps, (width, height))
                if self.out.isOpened():
                    self.logger.debug(f"VideoWriter opened with codec {codec}")
                    break
                self.logger.warning(f"Codec {codec} failed")
            else:
                self._set_error("Failed to initialize VideoWriter")
                self.out = None
                return

            self._state.is_recording = True
            self.logger.info(f"Recording started: {self.output_path}")

        else:
            if self.out is not None and self.out.isOpened():
                self.out.release()
                self.logger.debug("VideoWriter closed")
            self.out = None
            self._state.is_recording = False
            
            if not os.path.exists(self.output_path) or os.path.getsize(self.output_path) == 0:
                self._set_error(f"Recording file empty or not created: {self.output_path}")
            
            self.output_path = self._generate_output_path()
            self.logger.info("Recording stopped")

    def set_window_visible(self, visible: bool) -> None:
        """Управляет отображением окон камеры."""
        self.show_window = visible
        if visible and self._is_initialized and self.zed is not None:
            if not self.window_created:
                camera_info = self.zed.get_camera_information()
                width = camera_info.camera_configuration.resolution.width
                height = camera_info.camera_configuration.resolution.height
                cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
                cv2.namedWindow(self.depth_window_name, cv2.WINDOW_NORMAL)
                cv2.resizeWindow(self.window_name, width, height)
                cv2.resizeWindow(self.depth_window_name, width, height)
                self.window_created = True
                self.logger.debug("ZED camera windows created")
        elif not visible and self.window_created:
            try:
                cv2.destroyWindow(self.window_name)
                cv2.destroyWindow(self.depth_window_name)
                self.window_created = False
                self.logger.debug("ZED camera windows closed")
            except cv2.error as e:
                self._set_error(f"Error closing ZED windows: {e}")

    def set_steering_trim(self, trim: float) -> None:
        """Устанавливает значение трима руля."""
        self.steering_trim = trim
        self.logger.debug(f"ZED steering trim set to: {trim:.3f}")

    def increase_depth_threshold(self) -> None:
        """Увеличивает порог глубины."""
        self.depth_threshold += self.config.depth_step
        self.logger.debug(f"Depth threshold increased: {self.depth_threshold:.2f} m")

    def decrease_depth_threshold(self) -> None:
        """Уменьшает порог глубины."""
        self.depth_threshold = max(0.1, self.depth_threshold - self.config.depth_step)
        self.logger.debug(f"Depth threshold decreased: {self.depth_threshold:.2f} m")

    def reset_depth_threshold(self) -> None:
        """Сбрасывает порог глубины."""
        self.depth_threshold = self.config.depth_threshold
        self.logger.debug(f"Depth threshold reset: {self.depth_threshold:.2f} m")

    def close(self) -> None:
        """Закрывает камеру и освобождает ресурсы."""
        self.stop()
        if self._state.is_recording:
            self.toggle_recording()
        if self.zed is not None:
            self.zed.close()
            self.zed = None
        if self.window_created:
            try:
                cv2.destroyWindow(self.window_name)
                cv2.destroyWindow(self.depth_window_name)
                self.window_created = False
            except cv2.error as e:
                self._set_error(f"Error closing ZED windows: {e}")
        self._is_initialized = False
        self.logger.info("ZED camera closed") 