import serial
import multiprocessing
from src.utils.config import ConfigManager
from src.utils.logger import Logger


class CommunicationManager:
    def __init__(self):
        config = ConfigManager()
        self.port = config.get('arduino.port', '/dev/ttyUSB0')
        self.baudrate = config.get('arduino.baudrate', 9600)

        self.command_queue = multiprocessing.Queue()
        self.logger = Logger()
        self.is_running = multiprocessing.Value('b', True)
        self._connect()

    def _connect(self):
        try:
            self.serial_connection = serial.Serial(
                self.port,
                self.baudrate,
                timeout=1
            )
            self.logger.info(f"Connected to Arduino on {self.port}")
        except Exception as e:
            self.logger.error(f"Serial connection error: {e}")

    def send_commands(self):
        """Отправка команд на Arduino в отдельном процессе"""
        while self.is_running.value:
            try:
                if not self.command_queue.empty():
                    command = self.command_queue.get()
                    self._send_command(command)
            except Exception as e:
                self.logger.error(f"Command sending error: {e}")

    def _send_command(self, command):
        try:
            self.serial_connection.write(command.encode())
            self.logger.debug(f"Sent command: {command}")
        except Exception as e:
            self.logger.error(f"Failed to send command: {e}")

    def add_command(self, command):
        """Добавление команды в очередь"""
        if not self.command_queue.full():
            self.command_queue.put(command)
        else:
            self.logger.warning("Command queue is full")

    def stop(self):
        """Остановка коммуникации"""
        self.is_running.value = False
        if hasattr(self, 'serial_connection'):
            self.serial_connection.close()
