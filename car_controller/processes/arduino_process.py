from multiprocessing import Process

import serial

from ..core.config.settings import Settings
from ..core.logging import setup_logger
from ..core.communication import MessageBroker, ControlCommand, ArduinoCommand
from ..devices.output import Arduino


class ArduinoProcess(Process):
    def __init__(self, broker: MessageBroker, settings: Settings):
        super().__init__()
        self.command_queue = broker.get_queue('control_commands')
        self.arduino = Arduino(
            port=settings.arduino.port,
            baudrate=settings.arduino.baudrate
        )
        self.logger = setup_logger(__name__)

        # Константы для управления
        self.MOTOR_STOP = 90
        self.MOTOR_MAX_FORWARD = 180
        self.MOTOR_MAX_REVERSE = 0
        self.SERVO_CENTER = 90
        self.SERVO_LEFT = 45
        self.SERVO_RIGHT = 135

    def normalize_motor(self, speed: float, brake: float) -> int:
        if brake > 0:
            # Преобразуем тормоз в обратный ход
            return int(self.MOTOR_STOP + (self.MOTOR_STOP - self.MOTOR_MAX_REVERSE) * brake)
        else:
            # Преобразуем скорость в передний ход
            return int(self.MOTOR_STOP + (self.MOTOR_MAX_FORWARD - self.MOTOR_STOP) * speed)

    def normalize_steering(self, steering: float) -> int:
        # steering в диапазоне [-0.5, 0.5]
        # преобразуем в [45, 135]
        return int(self.SERVO_CENTER + (steering * (self.SERVO_RIGHT - self.SERVO_CENTER)))

    def convert_command(self, control_cmd: ControlCommand) -> ArduinoCommand:
        return ArduinoCommand(
            motor_value=self.normalize_motor(control_cmd.speed, control_cmd.brake),
            steering_value=self.normalize_steering(control_cmd.steering),
            timestamp=control_cmd.timestamp
        )

    def run(self):
        try:
            self.arduino.initialize()
            while True:
                control_cmd = self.command_queue.get()
                arduino_cmd = self.convert_command(control_cmd)
                try:
                    self.arduino.send_command(arduino_cmd)
                except serial.SerialException as e:
                    self.logger.error(f"Failed to send command: {e}")
        except Exception as e:
            self.logger.error(f"Arduino process error: {e}")
        finally:
            self.arduino.close()