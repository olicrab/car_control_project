import cv2
import multiprocessing
from src.utils.config import ConfigManager
from src.utils.logger import Logger

class CameraManager:
    def __init__(self):
        config = ConfigManager()
        self.camera_index = config.get('camera.index', 0)
        self.resolution = config.get('camera.resolution', (640, 480))
        self.frame_queue = multiprocessing.Queue(
            maxsize=config.get('processing.frame_queue_size', 10)
        )
        self.logger = Logger()
        self.is_running = multiprocessing.Value('b', True)

    def start_capture(self):
        """Захват кадров с камеры в отдельном процессе"""
        cap = None
        try:
            cap = cv2.VideoCapture(self.camera_index)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])

            while self.is_running.value:
                ret, frame = cap.read()
                if not ret:
                    self.logger.error("Failed to capture frame")
                    break

                if not self.frame_queue.full():
                    self.frame_queue.put(frame)
        except Exception as e:
            self.logger.error(f"Camera capture error: {e}")
        finally:
            if cap is not None:
                cap.release()

    def stop(self):
        """Остановка захвата кадров"""
        self.is_running.value = False
