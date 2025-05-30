import cv2
import os
import time
import logging
from core.interfaces.video_recorder import VideoRecorder

logger = logging.getLogger(__name__)

class ZEDVideoRecorder(VideoRecorder):
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        self.recording = False
        self.out = None
        self.output_path = self._generate_output_path()
        self.width = 1280
        self.height = 720
        self.fps = 30

    def _generate_output_path(self) -> str:
        timestamp = int(time.time())
        return os.path.join(self.output_dir, f"output_{timestamp}.avi")

    def initialize(self) -> None:
        if not os.access(self.output_dir, os.W_OK):
            logger.error(f"No write permissions for {self.output_dir}")
            raise RuntimeError("No write permissions")

    def toggle_recording(self) -> None:
        if not self.recording:
            codecs = ['XVID', 'MJPG', 'H264', 'DIVX']
            for codec in codecs:
                fourcc = cv2.VideoWriter_fourcc(*codec)
                self.out = cv2.VideoWriter(self.output_path, fourcc, self.fps, (self.width, self.height))
                if self.out.isOpened():
                    logger.debug(f"VideoWriter opened with codec {codec}")
                    break
            else:
                logger.error("Failed to initialize VideoWriter")
                raise RuntimeError("VideoWriter initialization failed")
            self.recording = True
            logger.info(f"Recording started: {self.output_path}")
        else:
            if self.out:
                self.out.release()
            self.recording = False
            logger.info("Recording stopped")
            self.output_path = self._generate_output_path()

    def record_frame(self, frame) -> None:
        if self.recording and self.out and self.out.isOpened():
            self.out.write(frame)
            logger.debug(f"Frame recorded: {frame.shape}")

    def close(self) -> None:
        if self.recording:
            self.toggle_recording()
        logger.info("VideoRecorder closed")