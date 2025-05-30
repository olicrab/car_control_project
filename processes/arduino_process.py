from multiprocessing import Process, Queue, Event
import logging
from core.interfaces.arduino_interface import ArduinoInterface

logger = logging.getLogger(__name__)

class ArduinoProcess(Process):
    def __init__(self, arduino: ArduinoInterface, command_queue: Queue, stop_event: Event):
        super().__init__()
        self.arduino = arduino
        self.command_queue = command_queue
        self.stop_event = stop_event

    def run(self) -> None:
        logger.info("Arduino process started")
        try:
            self.arduino.initialize()
            while not self.stop_event.is_set():
                try:
                    motor_value, steering_value = self.command_queue.get(timeout=1.0)
                    self.arduino.send_command(motor_value, steering_value)
                except Queue.Empty:
                    continue
        except Exception as e:
            logger.error(f"Arduino process error: {e}")
        finally:
            self.arduino.close()
            logger.info("Arduino process stopped")