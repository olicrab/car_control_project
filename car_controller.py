import serial
from speed import Speed

class CarController:
    def __init__(self, arduino_port='/dev/ttyUSB0'):
        self.arduino = serial.Serial(arduino_port, 9600)
        self.speed_modes = {
            'turtle': Speed(75, 105),
            'slow': Speed(70, 110),
            'medium': Speed(45, 120),
            'fast': Speed(0, 180)
        }
        self.current_speed_mode = 'medium'  # Начальный режим
        self.steering = 90  # Центр серво
        self.motor_value = 90  # Остановленный мотор
        self.default_motor_value = 90  # Значение по умолчанию для мотора

    def set_speed_mode(self, mode):
        """Устанавливает режим скорости (turtle, slow, medium, fast)."""
        if mode in self.speed_modes:
            self.current_speed_mode = mode
        else:
            print("Неизвестный режим скорости! Устанавливается средний.")
            self.current_speed_mode = 'medium'

    def increase_speed_mode(self):
        """Увеличивает режим скорости (при возможности)."""
        speed_modes = list(self.speed_modes.keys())
        current_index = speed_modes.index(self.current_speed_mode)
        if current_index < len(speed_modes) - 1:
            self.current_speed_mode = speed_modes[current_index + 1]
            print(f"Режим скорости увеличен: {self.current_speed_mode}")
        else:
            print("Вы уже на максимальном режиме!")

    def decrease_speed_mode(self):
        """Уменьшает режим скорости (при возможности)."""
        speed_modes = list(self.speed_modes.keys())
        current_index = speed_modes.index(self.current_speed_mode)
        if current_index > 0:
            self.current_speed_mode = speed_modes[current_index - 1]
            print(f"Режим скорости уменьшен: {self.current_speed_mode}")
        else:
            print("Вы уже на минимальном режиме!")

    def scale_motor_value(self, value, mode):
        """Масштабирует значение газа или тормоза в нужный диапазон в зависимости от текущего режима."""
        speed = self.speed_modes[mode]
        return speed.scale_gas(value, self.default_motor_value) if value >= 0 else speed.scale_brake(abs(value), self.default_motor_value)

    def send_command(self, motor_value, steering_value):
        """Отправляет команду на Arduino."""
        command = f"{motor_value},{steering_value}\n"
        self.arduino.write(command.encode())

    def update(self, gas, brake, steering_value):
        """Обновляет управление на основе значения газа, тормоза и поворота."""
        speed = self.speed_modes[self.current_speed_mode]
        if gas > 0:  # Если газ нажат
            self.motor_value = speed.scale_gas(gas, self.default_motor_value)  # Масштабируем значение газа
        else:  # Если тормоз нажат
            self.motor_value = speed.scale_brake(brake, self.default_motor_value)  # Масштабируем значение тормоза

        # Управляем серво
        if steering_value < -0.5:
            self.steering = 180  # Поворот влево
        elif steering_value > 0.5:
            self.steering = 0  # Поворот вправо
        else:
            self.steering = 90  # Центр серво

        # Отправляем команду на Arduino
        self.send_command(self.motor_value, self.steering)
