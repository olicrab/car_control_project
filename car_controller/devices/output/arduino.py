import serial
from .base_output import BaseOutput
from ...core.communication.message_types import ArduinoCommand


class Arduino(BaseOutput):
    def __init__(self, port='COM3', baudrate=115200):
        self.port = port
        self.baudrate = baudrate
        self.serial = None

    def initialize(self) -> None:
        self.serial = serial.Serial(self.port, self.baudrate)

    def send_command(self, command: ArduinoCommand) -> None:
        if not self.serial:
            return

        msg = f"{command.motor_value},{command.steering_value}\n"
        self.serial.write(msg.encode())

    def close(self) -> None:
        if self.serial:
            self.serial.close()