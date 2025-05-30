import serial
import logging
from core.interfaces.arduino_interface import ArduinoInterface

logger = logging.getLogger(__name__)

class ArduinoAdapter(ArduinoInterface):
    def __init__(self, port: str = '/dev/ttyUSB0', baud_rate: int = 9600):
        self.port = port
        self.baud_rate = baud_rate
        self.arduino = None

    def initialize(self) -> None:
        try:
            self.arduino = serial.Serial(self.port, self.baud_rate)
            logger.info(f"Arduino connected on {self.port}")
        except serial.SerialException as e:
            logger.error(f"Arduino initialization error: {e}")
            raise

    def send_command(self, motor_value: int, steering_value: int) -> None:
        command = f"{motor_value},{steering_value}\n"
        try:
            self.arduino.write(command.encode())
            logger.debug(f"Sent command: motor={motor_value}, steering={steering_value}")
        except serial.SerialException as e:
            logger.error(f"Error sending command: {e}")

    def close(self) -> None:
        if self.arduino:
            self.send_command(90, 90)  # Stop
            self.arduino.close()
        logger.info("Arduino disconnected")