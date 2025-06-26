from car_controller.car_controller import CarController
import time

def main():
    # Укажите COM-порт, к которому подключена Arduino (например, "COM3")
    arduino_port = "COM3"
    baud_rate = 9600

    try:
        # Инициализация контроллера автомобиля
        car = CarController(arduino_port=arduino_port, baud_rate=baud_rate)

        # Пример управления
        print("Установка передачи на 'medium'")
        car.set_gear("turtle")
        time.sleep(1)

        print("Увеличение скорости")
        car.update(speed=1, brake=0.0, steering=0.0)  # Половина скорости, без тормоза, без поворота
        time.sleep(2)

        print("Поворот налево")
        car.update(speed=1, brake=0.0, steering=-0.5)  # Поворот направо
        time.sleep(2)

        print("Прямо")
        car.update(speed=1, brake=0.0, steering=0)  # Поворот направо
        time.sleep(2)

        print("Поворот направо")
        car.update(speed=1, brake=0.0, steering=0.5)  # Поворот направо
        time.sleep(2)

        print("Торможение")
        car.update(speed=0.0, brake=1.0, steering=0.0)  # Полное торможение
        time.sleep(1)

        print("Остановка")
        car.stop()

    except Exception as e:
        print(f"Ошибка: {e}")
    finally:
        # Закрытие соединения
        car.close()
        print("Соединение с Arduino закрыто")

if __name__ == "__main__":
    main()
