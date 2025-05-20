import time
import pygame
import cv2
from car_controller.car_controller import CarController
from car_controller.gamepad_input import GamepadInput
from car_controller.camera_input import CameraInput

def main():
    pygame.init()

    # Инициализация компонентов
    controller = CarController('/dev/ttyUSB0')
    gamepad_input = GamepadInput(joystick_index=0)
    camera_input = CameraInput(device=0)

    # Инициализация геймпада
    try:
        gamepad_input.initialize()
    except RuntimeError as e:
        print(f"Ошибка инициализации геймпада: {e}")
        pygame.quit()
        return

    # Инициализация камеры
    try:
        camera_input.initialize()
    except RuntimeError as e:
        print(f"Ошибка инициализации камеры: {e}")
        pygame.quit()
        return

    # Начальный режим - геймпад
    is_gamepad_mode = True

    # Регистрация действий для геймпада
    def toggle_input_mode():
        nonlocal is_gamepad_mode
        is_gamepad_mode = not is_gamepad_mode
        camera_input.set_window_visible(not is_gamepad_mode)
        print(f"Режим ввода: {'геймпад' if is_gamepad_mode else 'камера'}")

    gamepad_input.register_button_action(5, controller.increase_speed_mode)  # Левый бампер
    gamepad_input.register_button_action(4, controller.decrease_speed_mode)  # Правый бампер
    gamepad_input.register_button_action(7, toggle_input_mode)  # Кнопка Start
    gamepad_input.register_button_action(0, camera_input.toggle_recording)  # Кнопка A

    print("Управление машинкой:")
    print(
        "Левый стик: поворот, триггеры: газ/тормоз, бамперы: смена режима, Start: переключение режима, A: запись видео, Q: выход")

    try:
        while True:
            # Всегда обрабатываем кнопки геймпада
            gamepad_input.get_input()

            # Получаем команды управления
            if is_gamepad_mode:
                gas, brake, steering, _, _ = gamepad_input.get_input()
            else:
                gas, brake, steering, _, _ = camera_input.get_input()

            # Всегда обрабатываем кадры с камеры для записи
            camera_input.get_input()

            controller.update(gas, brake, steering)

            # print(f"Мотор: {controller.motor_value}, Серво: {controller.steering}")

            # Проверка выхода по клавише Q
            if pygame.get_init():
                keys = pygame.key.get_pressed()
                if keys[pygame.K_q]:
                    print("Выход из программы.")
                    break

            # Обработка событий OpenCV в режиме камеры
            if not is_gamepad_mode:
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    print("Выход по клавише 'q' из режима камеры")
                    toggle_input_mode()

            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\nПрограмма завершена.")
    finally:
        if camera_input.recording:
            camera_input.toggle_recording()  # Завершаем запись
        controller.close()
        gamepad_input.close()
        camera_input.close()
        pygame.quit()

if __name__ == "__main__":
    main()