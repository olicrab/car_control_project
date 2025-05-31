from multiprocessing import Process, Queue, Event
import logging
from application.input_manager import InputManager

logger = logging.getLogger(__name__)

class InputProcess(Process):
    def __init__(self, input_manager: InputManager, command_queue: Queue, stop_event: Event):
        super().__init__()
        self.input_manager = input_manager
        self.command_queue = command_queue
        self.stop_event = stop_event
        logger.info("InputProcess initialized")

    def run(self) -> None:
        logger.info("Input process started")
        try:
            self.input_manager.initialize()
            while not self.stop_event.is_set():
                command = self.input_manager.get_command()
                self.command_queue.put(command)
        except Exception as e:
            logger.error(f"Input process error: {e}")
            self.input_manager.state_manager.update_state(last_error=f"Input process error: {e}")
        finally:
            self.input_manager.close()
            logger.info("Input process stopped")