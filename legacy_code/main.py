import pygame
import cv2
import curses
import logging.handlers
from legacy_code.car_controller import CarController
from legacy_code.gamepad_input import GamepadInput
from legacy_code.zed_camera_input import ZEDCameraInput

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.handlers.RotatingFileHandler('car_control.log', maxBytes=5*1024*1024, backupCount=3),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def curses_interface(stdscr, controller, gamepad_input, camera_input, is_gamepad_mode):
    """Displays parameters and errors in a console interface."""
    curses.curs_set(0)
    stdscr.timeout(50)

    stdscr.clear()
    stdscr.addstr(0, 0, "Car Control", curses.A_BOLD)
    mode = "Gamepad" if is_gamepad_mode else "ZED-Autopilot"
    stdscr.addstr(2, 0, f"Mode: {mode}")
    stdscr.addstr(4, 0, f"Speed: {controller.motor_value:3d}")
    stdscr.addstr(5, 0, f"Gear: {controller.adapter.current_gear}")
    stdscr.addstr(6, 0, f"Steering: {controller.steering:3d}")
    stdscr.addstr(7, 0, f"Trim: {gamepad_input.steering_trim:.3f}")
    stdscr.addstr(8, 0, f"Depth Threshold: {camera_input.depth_threshold:.2f} m")
    stdscr.addstr(9, 0, f"Min Distance: {camera_input.min_distance:.2f} m")
    stdscr.addstr(10, 0, f"Recording: {'On' if camera_input.recording else 'Off'}")
    stdscr.addstr(11, 0, f"Braking: {'On' if camera_input.braking else 'Off'}")
    stdscr.addstr(13, 0, f"Last Error: {camera_input.last_error or 'None'}")
    stdscr.addstr(15, 0, "Left Stick: steering, Triggers: throttle/brake, Bumpers: gears")
    stdscr.addstr(16, 0, "Start: mode, A: record, B: reverse, X: reset trim, Y: reset depth")
    stdscr.addstr(17, 0, "D-Pad: trim (left/right: ±2), depth (up/down: ±0.05)")
    stdscr.addstr(18, 0, "Q: exit")

    try:
        stdscr.refresh()
        return stdscr.getch()
    except curses.error:
        logger.error("Curses refresh error")
        return -1

def main(stdscr):
    """Main function with curses interface."""
    curses.noecho()
    curses.cbreak()
    stdscr.keypad(True)

    pygame.init()
    logger.info("Pygame initialized")

    controller = CarController('/dev/ttyUSB0')
    gamepad_input = GamepadInput(joystick_index=0)
    camera_input = ZEDCameraInput()

    try:
        gamepad_input.initialize()
        camera_input.initialize()
    except RuntimeError as e:
        logger.error(f"Initialization error: {e}")
        camera_input.last_error = f"Initialization error: {e}"
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
        logger.debug(f"Mode switched to: {'Gamepad' if is_gamepad_mode else 'ZED-Autopilot'}")

    def set_reverse_gear():
        controller.set_gear("reverse")
        logger.debug("Reverse gear set")

    gamepad_input.register_button_action(5, controller.increase_gear)
    gamepad_input.register_button_action(4, controller.decrease_gear)
    gamepad_input.register_button_action(7, toggle_input_mode)
    gamepad_input.register_button_action(0, camera_input.toggle_recording)
    gamepad_input.register_button_action(1, set_reverse_gear)
    gamepad_input.register_button_action(2, gamepad_input.reset_trim)
    gamepad_input.register_button_action(3, gamepad_input.reset_depth_threshold)

    try:
        while True:
            gamepad_input.get_input()
            speed, brake, steering, _, _ = gamepad_input.get_input() if is_gamepad_mode else camera_input.get_input()
            camera_input.get_input()
            controller.update(speed, brake, steering)

            key = curses_interface(stdscr, controller, gamepad_input, camera_input, is_gamepad_mode)
            if key == ord('q') or (not is_gamepad_mode and cv2.waitKey(1) & 0xFF == ord('q')):
                logger.info("Exiting by user request")
                break

    except Exception as e:
        logger.error(f"Runtime error: {e}")
        camera_input.last_error = f"Runtime error: {e}"
    finally:
        curses.nocbreak()
        stdscr.keypad(False)
        curses.echo()
        curses.endwin()
        if camera_input.recording:
            camera_input.toggle_recording()
        controller.stop()
        controller.close()
        gamepad_input.close()
        camera_input.close()
        pygame.quit()
        logger.info("Program terminated")

if __name__ == "__main__":
    curses.wrapper(main)