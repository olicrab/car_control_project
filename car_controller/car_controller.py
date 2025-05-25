import serial
from typing import Dict
from .gear import Gear, GearDirection
from .arduino_adapter import ArduinoAdapter

class CarController:
    def __init__(self, arduino_port: str = '/dev/ttyUSB0', baud_rate: int = 9600):
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
        print(f"Arduino подключен на {arduino_port} с baud rate {baud_rate}")

    def set_gear(self, gear: str) -> None:
        """Устанавливает передачу."""
        self.adapter.set_gear(gear)

    def increase_gear(self) -> None:
        """Увеличивает передачу."""
        self.adapter.increase_gear()

    def decrease_gear(self) -> None:
        """Уменьшает передачу."""
        self.adapter.decrease_gear()

    def update(self, speed: float, brake: float, steering: float) -> None:
        """Обновляет управление. Brake использует обратное направление."""
        self.motor_value, self.steering = self.adapter.convert_commands(speed, brake, steering)
        self.send_command(self.motor_value, self.steering)

    def send_command(self, motor_value: int, steering_value: int) -> None:
        """Отправляет команду на Arduino."""
        command = f"{motor_value},{steering_value}\n"
        try:
            self.arduino.write(command.encode())
        except serial.SerialException as e:
            print(f"Ошибка отправки команды на Arduino: {e}")

    def stop(self) -> None:
        """Останавливает машинку (мотор = 90, руль = 90)."""
        self.send_command(90, 90)
        self.motor_value = 90
        self.steering = 90

    def close(self) -> None:
        """Закрывает соединение с Arduino."""
        self.stop()  # Остановка перед закрытием
        self.arduino.close()
        print("Arduino отключен")