import serial
import logging
import logging.handlers
from typing import Dict
from .gear import Gear, GearDirection
from .arduino_adapter import ArduinoAdapter

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.handlers.RotatingFileHandler('car_control.log', maxBytes=5*1024*1024, backupCount=3),
        logging.StreamHandler()  # For initialization
    ]
)
logger = logging.getLogger(__name__)

class CarController:
    def __init__(self, arduino_port: str = '/dev/ttyUSB0', baud_rate: int = 9600):
        try:
            self.arduino = serial.Serial(arduino_port, baud_rate)
            self.adapter = ArduinoAdapter(
                gears={
                    "turtle": Gear(max_speed=15, direction=GearDirection.FORWARD),
                    "slow": Gear(max_speed=30, direction=GearDirection.FORWARD),
                    "medium": Gear(max_speed=50, direction=GearDirection.FORWARD),
                    "fast": Gear(max_speed=100, direction=GearDirection.FORWARD)
                },
                default_gear="turtle"
            )
            self.motor_value = 90
            self.steering = 90
            logger.info(f"Arduino connected on {arduino_port} with baud rate {baud_rate}")
        except serial.SerialException as e:
            logger.error(f"Arduino initialization error: {e}")
            raise

    def set_gear(self, gear: str) -> None:
        """Sets the gear."""
        self.adapter.set_gear(gear)

    def increase_gear(self) -> None:
        """Increases the gear."""
        self.adapter.increase_gear()

    def decrease_gear(self) -> None:
        """Decreases the gear."""
        self.adapter.decrease_gear()

    def update(self, speed: float, brake: float, steering: float) -> None:
        """Updates control. Brake uses reverse direction."""
        self.motor_value, self.steering = self.adapter.convert_commands(speed, brake, steering)
        self.send_command(self.motor_value, self.steering)

    def send_command(self, motor_value: int, steering_value: int) -> None:
        """Sends command to Arduino."""
        command = f"{motor_value},{steering_value}\n"
        try:
            self.arduino.write(command.encode())
            logger.debug(f"Sent command: motor={motor_value}, steering={steering_value}")
        except serial.SerialException as e:
            logger.error(f"Error sending command to Arduino: {e}")

    def stop(self) -> None:
        """Stops the car (motor = 90, steering = 90)."""
        self.send_command(90, 90)
        self.motor_value = 90
        self.steering = 90
        logger.info("Car stopped")

    def close(self) -> None:
        """Closes Arduino connection."""
        self.stop()
        self.arduino.close()
        logger.info("Arduino disconnected")