import cv2
import os
import time
import logging
from core.interfaces.video_recorder import VideoRecorder
from application.state_manager import StateManager

logger = logging.getLogger(__name__)

class ZEDVideoRecorder(VideoRecorder):
    def __init__(self, output_dir: str, state_manager: StateManager):
        self.output_dir = output_dir
        self.state_manager = state_manager
        self.recording = False
        self.out = None
        self.output_path = self._generate_output_path()
        self.width = 1280
        self.height = 720
        self.fps = 30
        logger.info(f"ZEDVideoRecorder initialized with output_dir: {output_dir}")

    def _generate_output_path(self) -> str:
        timestamp = int(time.time())
        return os.path.join(self.output_dir, f"output_{timestamp}.avi")

    def initialize(self) -> None:
        os.makedirs(self.output_dir, exist_ok=True)
        if not os.access(self.output_dir, os.W_OK):
            logger.error(f"No write permissions for {self.output_dir}")
            self.state_manager.update_state(last_error=f"No write permissions for {self.output_dir}")
            raise RuntimeError("No write permissions")
        logger.info("ZEDVideoRecorder initialized")

    def toggle_recording(self) -> None:
        try:
            if not self.recording:
                fourcc = cv2.VideoWriter_fourcc(*'MJPG')  # Используем MJPG
                self.out = cv2.VideoWriter(self.output_path, fourcc, self.fps, (self.width, self.height))
                if not self.out.isOpened():
                    logger.error("Failed to initialize VideoWriter")
                    self.state_manager.update_state(last_error="Failed to initialize VideoWriter")
                    raise RuntimeError("VideoWriter initialization failed")
                self.recording = True
                self.state_manager.update_state(recording=True)
                logger.info(f"Recording started: {self.output_path}")
            else:
                if self.out:
                    self.out.release()
                    self.out = None
                self.recording = False
                self.state_manager.update_state(recording=False)
                logger.info("Recording stopped")
                self.output_path = self._generate_output_path()
        except Exception as e:
            logger.error(f"Error toggling recording: {e}")
            self.state_manager.update_state(last_error=f"Error toggling recording: {e}")

    def record_frame(self, frame) -> None:
        try:
            if self.recording and self.out and self.out.isOpened():
                logger.debug(f"Input frame shape: {frame.shape}")
                if frame.shape[2] == 4:  # RGBA
                    frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2RGB)
                elif frame.shape[2] == 3 and frame[:,:,0].mean() > frame[:,:,2].mean():  # BGR
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                if frame.shape[1] != self.width or frame.shape[0] != self.height:
                    frame = cv2.resize(frame, (self.width, self.height))
                    logger.debug(f"Resized frame to {self.width}x{self.height}")
                self.out.write(frame)
                logger.debug(f"Frame recorded: {frame.shape}")
        except Exception as e:
            logger.error(f"Error recording frame: {e}")
            self.state_manager.update_state(last_error=f"Error recording frame: {e}")

    def close(self) -> None:
        try:
            if self.recording:
                self.toggle_recording()
            if self.out:
                self.out.release()
                self.out = None
            logger.info("VideoRecorder closed")
        except Exception as e:
            logger.error(f"Error closing VideoRecorder: {e}")
            self.state_manager.update_state(last_error=f"Error closing VideoRecorder: {e}")