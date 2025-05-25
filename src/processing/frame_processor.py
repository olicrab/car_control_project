import cv2
import multiprocessing
from src.utils.config import ConfigManager
from src.utils.logger import Logger


class FrameProcessor:
    def __init__(self, frame_queue, processed_queue):
        config = ConfigManager()
        self.frame_queue = frame_queue
        self.processed_queue = processed_queue
        self.logger = Logger()
        self.debug_mode = config.get('processing.debug_mode', False)
        self.is_running = multiprocessing.Value('b', True)

    def process_frames(self):
        """Обработка кадров в отдельном процессе"""
        while self.is_running.value:
            try:
                if not self.frame_queue.empty():
                    frame = self.frame_queue.get()
                    processed_frame = self._process_frame(frame)

                    if not self.processed_queue.full():
                        self.processed_queue.put(processed_frame)

                    if self.debug_mode:
                        self._debug_visualization(processed_frame)
            except Exception as e:
                self.logger.error(f"Frame processing error: {e}")

    def _process_frame(self, frame):
        """Базовая обработка кадра"""
        # Пример: детекция краев
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 100, 200)
        return edges

    def _debug_visualization(self, frame):
        """Визуализация обработанного кадра"""
        cv2.imshow('Processed Frame', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            self.stop()

    def stop(self):
        """Остановка обработки кадров"""
        self.is_running.value = False
