
import serial
from typing import Dict
from .speed import Speed

class CarController:
    def __init__(self, arduino_port: str = '/dev/ttyUSB0', baud_rate: int = 9600):
        self.arduino = serial.Serial(arduino_port, baud_rate)
        self.speed_modes: Dict[str, Speed] = {
            'turtle': Speed(75, 105),
            'slow': Speed(70, 110),
            'medium': Speed(45, 120),
            'fast': Speed(0, 180)
        }
        self.current_speed_mode = 'medium'
        self.steering = 90  # Центр серво
        self.motor_value = 90  # Остановленный мотор
        self.default_motor_value = 90

    def set_speed_mode(self, mode: str) -> None:
        """Устанавливает режим скорости."""
        if mode in self.speed_modes:
            self.current_speed_mode = mode
        else:
            print(f"Неизвестный режим скорости: {mode}. Устанавливается 'medium'.")
            self.current_speed_mode = 'medium'

    def increase_speed_mode(self) -> None:
        """Увеличивает режим скорости."""
        speed_modes = list(self.speed_modes.keys())
        current_index = speed_modes.index(self.current_speed_mode)
        if current_index < len(speed_modes) - 1:
            self.current_speed_mode = speed_modes[current_index + 1]
            print(f"Режим скорости увеличен: {self.current_speed_mode}")
        else:
            print("Вы уже на максимальном режиме!")

    def decrease_speed_mode(self) -> None:
        """Уменьшает режим скорости."""
        speed_modes = list(self.speed_modes.keys())
        current_index = speed_modes.index(self.current_speed_mode)
        if current_index > 0:
            self.current_speed_mode = speed_modes[current_index - 1]
            print(f"Режим скорости уменьшен: {self.current_speed_mode}")
        else:
            print("Вы уже на минимальном режиме!")

    def scale_motor_value(self, value: float) -> int:
        """Масштабирует значение газа или тормоза в зависимости от режима."""
        speed = self.speed_modes[self.current_speed_mode]
        return speed.scale_gas(value, self.default_motor_value) if value >= 0 else speed.scale_brake(abs(value), self.default_motor_value)

    def send_command(self, motor_value: int, steering_value: int) -> None:
        """Отправляет команду на Arduino."""
        command = f"{motor_value},{steering_value}\n"
        self.arduino.write(command.encode())

    def update(self, gas: float, brake: float, steering_value: float) -> None:
        """Обновляет управление на основе газа, тормоза и поворота."""
        self.motor_value = self.scale_motor_value(gas if gas > 0 else -brake)
        self.steering = 180 if steering_value < -0.5 else 0 if steering_value > 0.5 else 90
        self.send_command(self.motor_value, self.steering)

    def close(self) -> None:
        """Закрывает соединение с Arduino."""
        self.arduino.close()