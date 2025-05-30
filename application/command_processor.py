from multiprocessing import Queue
from core.entities.command import CarCommand
from .car_controller import CarController
from .input_manager import InputManager

class CommandProcessor:
    def __init__(self, input_manager: InputManager, car_controller: CarController, command_queue: Queue):
        self.input_manager = input_manager
        self.car_controller = car_controller
        self.command_queue = command_queue

    def process(self) -> None:
        while True:
            try:
                command = self.command_queue.get(timeout=1.0)
                self.car_controller.process_command(command)
            except Queue.Empty:
                continue