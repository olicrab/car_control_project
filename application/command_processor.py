from multiprocessing import Queue
from core.entities.command import CarCommand
from .car_controller import CarController
from .input_manager import InputManager
import logging
import queue

logger = logging.getLogger(__name__)

class CommandProcessor:
    def __init__(self, input_manager: InputManager, car_controller: CarController, command_queue: Queue):
        self.input_manager = input_manager
        self.car_controller = car_controller
        self.command_queue = command_queue
        logger.info("CommandProcessor initialized")

    def process(self) -> None:
        logger.info("CommandProcessor started")
        while True:
            try:
                command = self.command_queue.get(timeout=0.1)
                logger.debug(f"Processing command: speed={command.speed:.2f}, brake={command.brake:.2f}, steering={command.steering:.2f}")
                self.car_controller.process_command(command)
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error processing command: {e}")
                self.input_manager.state_manager.update_state(last_error=f"Command process error: {e}")
                break