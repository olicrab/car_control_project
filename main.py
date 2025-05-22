import time
import pygame
import cv2
from car_controller.car_controller import CarController
from car_controller.gamepad_input import GamepadInput
from car_controller.zed_camera_input import ZEDCameraInput

def main():
    pygame.init()

    controller = CarController('/dev/ttyUSB0')
    gamepad_input = GamepadInput(joystick_index=0)
    camera_input = ZEDCameraInput()

    try:
        gamepad_input.initialize()
    except RuntimeError as e:
        print(f"Ошибка инициализации геймпада: {e}")
        pygame.quit()
        return

    try:
        camera_input.initialize()
    except RuntimeError as e:
        print(f"Ошибка инициализации камеры: {e}")
        pygame.quit()
        return

    is_gamepad_mode = True

    def toggle_input_mode():
        nonlocal is_gamepad_mode
        is_gamepad_mode = not is_gamepad_mode
        camera_input.set_window_visible(not is_gamepad_mode)
        # Синхронизируем trim при переключении режима
        if is_gamepad_mode:
            gamepad_input.set_steering_trim(camera_input.steering_trim)
        else:
            camera_input.set_steering_trim(gamepad_input.steering_trim)
        print(f"Режим ввода: {'геймпад' if is_gamepad_mode else 'ZED-автопилот'}")

    def set_reverse_gear():
        controller.set_gear("reverse")
        print("Включена задняя передача")

    # Регистрация действий для кнопок
    gamepad_input.register_button_action(5, controller.increase_gear)  # Левый бампер
    gamepad_input.register_button_action(4, controller.decrease_gear)  # Правый бампер
    gamepad_input.register_button_action(7, toggle_input_mode)         # Start
    gamepad_input.register_button_action(0, camera_input.toggle_recording)  # A
    gamepad_input.register_button_action(1, set_reverse_gear)          # B

    print("Управление машинкой:")
    print("Левый стик: поворот, триггеры: газ/тормоз, бамперы: смена передачи, Start: режим, A: запись, B: задняя, D-Pad: trim (влево/вправо: ±2, вверх: сброс), Q: выход")

    try:
        while True:
            gamepad_input.get_input()
            speed, brake, steering, _, _ = gamepad_input.get_input() if is_gamepad_mode else camera_input.get_input()
            camera_input.get_input()  # Для записи и отображения
            controller.update(speed, brake, steering)
            print(f"Мотор: {controller.motor_value}, Серво: {controller.steering}, Trim: {gamepad_input.steering_trim:.3f}")
            if pygame.get_init():
                keys = pygame.key.get_pressed()
                if keys[pygame.K_q]:
                    print("Выход из программы.")
                    break
            if not is_gamepad_mode and cv2.waitKey(1) & 0xFF == ord('q'):
                print("Выход по клавише 'q' из режима автопилота")
                toggle_input_mode()
            time.sleep(0.05)
    except KeyboardInterrupt:
        print("\nПрограмма завершена.")
    finally:
        if camera_input.recording:
            camera_input.toggle_recording()
        controller.close()
        gamepad_input.close()
        camera_input.close()
        pygame.quit()

if __name__ == "__main__":
    main()