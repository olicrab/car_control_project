import multiprocessing
import time
from src.devices.gamepad_manager import GamepadManager
from src.devices.camera_manager import CameraManager
from src.processing.input_processor import InputProcessor
from src.processing.autopilot_processor import AutopilotProcessor
from src.utils.logger import Logger


class CarController:
    def __init__(self):
        self.logger = Logger()

        # Очереди для межпроцессного взаимодействия
        self.input_queue = multiprocessing.Queue()
        self.control_mode_queue = multiprocessing.Queue()
        self.output_queue = multiprocessing.Queue()

        # Инициализация компонентов
        self.camera_manager = CameraManager()
        self.autopilot_processor = AutopilotProcessor()

        self.input_processor = InputProcessor(
            self.input_queue,
            self.output_queue,
            self.autopilot_processor
        )

        self.gamepad_manager = GamepadManager(
            self.input_queue,
            self.control_mode_queue
        )

    def start(self):
        processes = [
            multiprocessing.Process(target=self.camera_manager.run),
            multiprocessing.Process(target=self.gamepad_manager.run),
            multiprocessing.Process(target=self.input_processor.process)
        ]

        for p in processes:
            p.start()

        self._control_loop()

    def _control_loop(self):
        while True:
            try:
                # Обработка смены режимов
                if not self.control_mode_queue.empty():
                    mode = self.control_mode_queue.get()
                    if mode == 'TOGGLE_AUTOPILOT':
                        self.input_processor.toggle_control_mode()

                # Получение и отправка команд
                if not self.output_queue.empty():
                    commands = self.output_queue.get()
                    self._send_commands(commands)

                time.sleep(0.1)
            except KeyboardInterrupt:
                break

    def _send_commands(self, commands):
        # Логика отправки команд на Arduino
        self.logger.debug(f"Sending commands: {commands}")

    def stop(self):
        # Логика остановки всех процессов
        pass
