import time
import pygame
from car_controller.car_controller import CarController
from car_controller.gamepad_input import GamepadInput

def main(input_type: str = "gamepad"):
    # Инициализация pygame для обработки клавиатуры
    pygame.init()

    # Инициализация компонентов
    controller = CarController('/dev/ttyUSB0')
    input_device = GamepadInput(joystick_index=0)
    input_device.initialize()

    # Регистрация действий для бамперов
    input_device.register_button_action(5, controller.increase_speed_mode)  # Левый бампер
    input_device.register_button_action(4, controller.decrease_speed_mode)  # Правый бампер

    print("Управление машинкой с геймпадом:")
    print("Левый стик: поворот, триггеры: газ/тормоз, бамперы: смена режима, Q: выход")

    try:
        while True:
            gas, brake, steering, _, _ = input_device.get_input()
            controller.update(gas, brake, steering)

            # Для отладки
            print(f"Мотор: {controller.motor_value}, Серво: {controller.steering}")

            # Проверка выхода по клавише Q
            keys = pygame.key.get_pressed()
            if keys[pygame.K_q]:
                print("Выход из программы.")
                break

            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\nПрограмма завершена.")
    finally:
        controller.close()
        input_device.close()
        pygame.quit()

if __name__ == "__main__":
    main(input_type="gamepad")