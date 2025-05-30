from multiprocessing import Queue, Event
import logging
from .input_process import InputProcess
from .command_process import CommandProcess
from .arduino_process import ArduinoProcess
from .ui_process import UIProcess

logger = logging.getLogger(__name__)

class ProcessManager:
    def __init__(self, input_process: InputProcess, command_process: CommandProcess,
                 arduino_process: ArduinoProcess, ui_process: UIProcess):
        self.input_process = input_process
        self.command_process = command_process
        self.arduino_process = arduino_process
        self.ui_process = ui_process

    def start(self) -> None:
        logger.info("Starting processes")
        self.input_process.start()
        self.command_process.start()
        self.arduino_process.start()
        self.ui_process.start()

    def stop(self) -> None:
        logger.info("Stopping processes")
        self.input_process.terminate()
        self.command_process.terminate()
        self.arduino_process.terminate()
        self.ui_process.terminate()
        self.input_process.join()
        self.command_process.join()
        self.arduino_process.join()
        self.ui_process.join()
        logger.info("All processes stopped")