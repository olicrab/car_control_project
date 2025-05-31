from multiprocessing import Process, Event
import logging
from application.command_processor import CommandProcessor

logger = logging.getLogger(__name__)

class CommandProcess(Process):
    def __init__(self, command_processor: CommandProcessor, stop_event: Event):
        super().__init__()
        self.command_processor = command_processor
        self.stop_event = stop_event
        logger.info("CommandProcess initialized")

    def run(self) -> None:
        logger.info("Command process started")
        try:
            while not self.stop_event.is_set():
                self.command_processor.process()
        except Exception as e:
            logger.error(f"Command process error: {e}")
            self.command_processor.input_manager.state_manager.update_state(last_error=f"Command process error: {e}")
        finally:
            logger.info("Command process stopped")