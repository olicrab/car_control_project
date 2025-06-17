import time
import pygame
import cv2
import curses
import logging
import logging.handlers
from typing import Optional
from input.gamepad import GamepadInput
from input.zed_camera import ZEDCameraInput
from config import Config

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.handlers.RotatingFileHandler('car_control.log', maxBytes=5*1024*1024, backupCount=3),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def curses_interface(stdscr, gamepad_input: GamepadInput, camera_input: ZEDCameraInput, is_gamepad_mode: bool) -> int:
    """Отображает параметры и ошибки в консольном интерфейсе."""
    curses.curs_set(0)
    stdscr.timeout(50)

    stdscr.clear()
    stdscr.addstr(0, 0, "Управление автомобилем", curses.A_BOLD)
    mode = "Геймпад" if is_gamepad_mode else "ZED-Автопилот"
    stdscr.addstr(2, 0, f"Режим: {mode}")
    stdscr.addstr(4, 0, f"Скорость: {gamepad_input.state.speed:.2f}")
    stdscr.addstr(5, 0, f"Тормоз: {gamepad_input.state.brake:.2f}")
    stdscr.addstr(6, 0, f"Руль: {gamepad_input.state.steering:.2f}")
    stdscr.addstr(7, 0, f"Трим: {gamepad_input.steering_trim:.3f}")
    stdscr.addstr(8, 0, f"Порог глубины: {camera_input.depth_threshold:.2f} м")
    stdscr.addstr(9, 0, f"Мин. расстояние: {camera_input.min_distance:.2f} м")
    stdscr.addstr(10, 0, f"Запись: {'Вкл' if camera_input.state.is_recording else 'Выкл'}")
    stdscr.addstr(11, 0, f"Торможение: {'Вкл' if camera_input.braking else 'Выкл'}")
    stdscr.addstr(13, 0, f"Последняя ошибка: {camera_input.last_error or 'Нет'}")
    stdscr.addstr(15, 0, "Левый стик: руль, Триггеры: газ/тормоз")
    stdscr.addstr(16, 0, "Start: режим, A: запись, B: задний ход, X: сброс трима, Y: сброс глубины")
    stdscr.addstr(17, 0, "D-Pad: трим (влево/вправо: ±2), глубина (вверх/вниз: ±0.1)")
    stdscr.addstr(18, 0, "Q: выход")

    try:
        stdscr.refresh()
        return stdscr.getch()
    except curses.error:
        logger.error("Ошибка обновления curses")
        return -1

def main(stdscr):
    """Основная функция с интерфейсом curses."""
    curses.noecho()
    curses.cbreak()
    stdscr.keypad(True)

    pygame.init()
    logger.info("Pygame инициализирован")

    config = Config()
    gamepad_input = GamepadInput(config.gamepad)
    camera_input = ZEDCameraInput(config.camera)

    try:
        gamepad_input.initialize()
        camera_input.initialize()
    except RuntimeError as e:
        logger.error(f"Ошибка инициализации: {e}")
        camera_input.last_error = f"Ошибка инициализации: {e}"
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
            logger.debug("Переключено в режим геймпада")
        else:
            camera_input.set_steering_trim(gamepad_input.steering_trim)
            logger.debug("Переключено в режим ZED-Автопилота")

    def set_reverse_gear():
        gamepad_input.state.gear = "reverse"
        logger.debug("Установлена задняя передача")

    gamepad_input.register_button_action(5, lambda: setattr(gamepad_input.state, 'gear', "forward"))
    gamepad_input.register_button_action(4, lambda: setattr(gamepad_input.state, 'gear', "forward"))
    gamepad_input.register_button_action(7, toggle_input_mode)
    gamepad_input.register_button_action(0, camera_input.toggle_recording)
    gamepad_input.register_button_action(1, set_reverse_gear)
    gamepad_input.register_button_action(2, gamepad_input.reset_trim)
    gamepad_input.register_button_action(3, camera_input.reset_depth_threshold)

    try:
        while True:
            if is_gamepad_mode:
                gamepad_input.update()
            else:
                camera_input.update()

            key = curses_interface(stdscr, gamepad_input, camera_input, is_gamepad_mode)
            if key == ord('q') or (not is_gamepad_mode and cv2.waitKey(1) & 0xFF == ord('q')):
                logger.info("Выход по запросу пользователя")
                break

    except Exception as e:
        logger.error(f"Ошибка выполнения: {e}")
        camera_input.last_error = f"Ошибка выполнения: {e}"
    finally:
        curses.nocbreak()
        stdscr.keypad(False)
        curses.echo()
        curses.endwin()
        if camera_input.state.is_recording:
            camera_input.toggle_recording()
        gamepad_input.close()
        camera_input.close()
        pygame.quit()
        logger.info("Программа завершена")

if __name__ == "__main__":
    curses.wrapper(main) 