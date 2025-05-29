import time
from multiprocessing import Process

from ..core.config.settings import Settings
from ..core.logging import setup_logger
from ..core.communication import CameraFrame
from ..core.communication import MessageBroker
from ..devices.camera import ZEDCamera
from ..vision.processors import DepthProcessor


class CameraProcess(Process):
    def __init__(self, broker: MessageBroker, settings: Settings):
        super().__init__()
        self.frame_queue = broker.create_queue('camera_frames')
        self.camera = ZEDCamera()
        self.processor = DepthProcessor(settings)  # Передаем настройки
        self.logger = setup_logger(__name__)

    def run(self):
        try:
            self.camera.initialize()
            while True:
                try:
                    image, depth = self.camera.get_frame()
                    if image is None or depth is None:
                        self.logger.warning("Failed to get frame")
                        continue

                    processed_image, processed_depth = self.processor.process(image, depth)
                    frame = CameraFrame(
                        image=processed_image,
                        depth=processed_depth,
                        timestamp=time.time()
                    )
                    self.frame_queue.put(frame)
                except Exception as e:
                    self.logger.error(f"Error processing frame: {e}")
        except Exception as e:
            self.logger.error(f"Camera process error: {e}")
        finally:
            self.camera.close()