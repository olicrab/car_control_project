import time
import pygame
import cv2
import curses
from car_controller.car_controller import CarController
from car_controller.gamepad_input import GamepadInput
from car_controller.zed_camera_input import ZEDCameraInput

def curses_interface(stdscr, controller, gamepad_input, camera_input, is_gamepad_mode):
    """Отображает параметры в консольном интерфейсе."""
    curses.curs_set(0)  # Скрыть курсор
    stdscr.timeout(50)  # Обновление каждые 50 мс

    while True:
        stdscr.clear()
        # Заголовок
        stdscr.addstr(0, 0, "Управление машинкой", curses.A_BOLD)
        # Режим
        mode = "Геймпад" if is_gamepad_mode else "ZED-автопилот"
        stdscr.addstr(2, 0, f"Режим: {mode}")
        # Параметры
        stdscr.addstr(4, 0, f"Скорость: {controller.motor_value:3d}")
        stdscr.addstr(5, 0, f"Передача: {controller.adapter.current_gear}")
        stdscr.addstr(6, 0, f"Поворот: {controller.steering:3d}")
        stdscr.addstr(7, 0, f"Trim: {gamepad_input.steering_trim:.3f}")
        stdscr.addstr(8, 0, f"Depth threshold: {camera_input.depth_threshold:.2f} м")
        stdscr.addstr(9, 0, f"Запись: {'Вкл' if camera_input.recording else 'Выкл'}")
        # Инструкции
        stdscr.addstr(11, 0, "Левый стик: поворот, триггеры: газ/тормоз, бамперы: передачи")
        stdscr.addstr(12, 0, "Start: режим, A: запись, B: задняя, X: сброс trim, Y: сброс depth")
        stdscr.addstr(13, 0, "D-Pad: trim (влево/вправо: ±2), depth (вверх/вниз: ±0.05)")
        stdscr.addstr(14, 0, "Q: выход")

        try:
            stdscr.refresh()
            return stdscr.getch()  # Возвращает код клавиши или -1
        except curses.error:
            return -1

def main():
    pygame.init()

    controller = CarController('/dev/ttyUSB0')
    gamepad_input = GamepadInput(joystick_index=0)
    camera_input = ZEDCameraInput()

    try:
        gamepad_input.initialize()
        camera_input.initialize()
    except RuntimeError as e:
        print(f"Ошибка инициализации: {e}")
        controller.stop()
        controller.close()
        gamepad_input.close()
        camera_input.close()
        pygame.quit()
        return

    gamepad_input.set_camera_input(camera_input)
    camera_input.set_gamepad_input(gamepad_input)

    is_gamepad_mode = True

    def toggle_input_mode():
        nonlocal is_gamepad_mode
        is_gamepad_mode = not is_gamepad_mode
        camera_input.set_window_visible(not is_gamepad_mode)
        if is_gamepad_mode:
            gamepad_input.set_steering_trim(camera_input.steering_trim)
        else:
            camera_input.set_steering_trim(gamepad_input.steering_trim)

    def set_reverse_gear():
        controller.set_gear("reverse")

    gamepad_input.register_button_action(5, controller.increase_gear)
    gamepad_input.register_button_action(4, controller.decrease_gear)
    gamepad_input.register_button_action(7, toggle_input_mode)
    gamepad_input.register_button_action(0, camera_input.toggle_recording)
    gamepad_input.register_button_action(1, set_reverse_gear)
    gamepad_input.register_button_action(2, gamepad_input.reset_trim)
    gamepad_input.register_button_action(3, gamepad_input.reset_depth_threshold)

    try:
        # Запускаем curses
        stdscr = curses.initscr()
        curses.noecho()
        curses.cbreak()
        stdscr.keypad(True)

        while True:
            gamepad_input.get_input()
            speed, brake, steering, _, _ = gamepad_input.get_input() if is_gamepad_mode else camera_input.get_input()
            camera_input.get_input()
            controller.update(speed, brake, steering)

            # Обновляем интерфейс и проверяем ввод
            key = curses.wrapper(lambda stdscr: curses_interface(stdscr, controller, gamepad_input, camera_input, is_gamepad_mode))
            if key == ord('q') or (not is_gamepad_mode and cv2.waitKey(1) & 0xFF == ord('q')):
                break

    except Exception as e:
        print(f"Ошибка: {e}")
    finally:
        # Восстанавливаем терминал
        curses.nocbreak()
        stdscr.keypad(False)
        curses.echo()
        curses.endwin()
        # Безопасное завершение
        if camera_input.recording:
            camera_input.toggle_recording()
        controller.stop()
        controller.close()
        gamepad_input.close()
        camera_input.close()
        pygame.quit()
        print("Программа завершена")

if __name__ == "__main__":
    main()