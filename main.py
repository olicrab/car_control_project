from car_controller import CarController
from gamepad_controller import GamepadController
import time

def main():
    # Создаём объекты для управления машинкой и геймпадом
    car = CarController('/dev/ttyUSB0')
    gamepad = GamepadController()

    print("Управление машинкой с геймпадом:")
    print("Используйте левый стик для поворотов.")
    print("Триггеры для газа и тормоза.")
    print("Нажмите на правый бампер для увеличения режима.")
    print("Нажмите на левый бампер для уменьшения режима.")
    print("Q - Выход")

    try:
        while True:
            # Получаем ввод с геймпада
            gas, brake, steering = gamepad.get_input()
            button_left_bumper, button_right_bumper = gamepad.get_button_press()

            # Обрабатываем бамперы для изменения режима
            if button_right_bumper:
                car.increase_speed_mode()

            if button_left_bumper:
                car.decrease_speed_mode()

            # Обновляем управление машинкой
            car.update(gas, brake, steering)

            # Для отладки выводим значения
            print(f"Мотор: {car.motor_value}, Серво: {car.steering}")

            # Выход по нажатию кнопки "Q"
            if pygame.key.get_pressed()[pygame.K_q]:
                print("Выход из программы.")
                break

            time.sleep(0.05)  # Небольшая задержка для предотвращения дребезга

    except KeyboardInterrupt:
        print("\nПрограмма завершена.")
    finally:
        car.arduino.close()
        pygame.quit()

if __name__ == "__main__":
    main()
