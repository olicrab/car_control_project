import time
import pygame
import cv2
import curses
from car_controller.car_controller import CarController
from car_controller.gamepad_input import GamepadInput
from car_controller.zed_camera_input import ZEDCameraInput

def curses_interface(stdscr, controller, gamepad_input, camera_input, is_gamepad_mode):
    """Displays parameters in a console interface."""
    curses.curs_set(0)  # Hide cursor
    stdscr.timeout(50)  # Refresh every 50 ms

    stdscr.clear()
    # Header
    stdscr.addstr(0, 0, "Car Control", curses.A_BOLD)
    # Mode
    mode = "Gamepad" if is_gamepad_mode else "ZED-Autopilot"
    stdscr.addstr(2, 0, f"Mode: {mode}")
    # Parameters
    stdscr.addstr(4, 0, f"Speed: {controller.motor_value:3d}")
    stdscr.addstr(5, 0, f"Gear: {controller.adapter.current_gear}")
    stdscr.addstr(6, 0, f"Steering: {controller.steering:3d}")
    stdscr.addstr(7, 0, f"Trim: {gamepad_input.steering_trim:.3f}")
    stdscr.addstr(8, 0, f"Depth Threshold: {camera_input.depth_threshold:.2f} m")
    stdscr.addstr(9, 0, f"Min Distance: {camera_input.min_distance:.2f} m")
    stdscr.addstr(10, 0, f"Recording: {'On' if camera_input.recording else 'Off'}")
    # Instructions
    stdscr.addstr(12, 0, "Left Stick: steering, Triggers: throttle/brake, Bumpers: gears")
    stdscr.addstr(13, 0, "Start: mode, A: record, B: reverse, X: reset trim, Y: reset depth")
    stdscr.addstr(14, 0, "D-Pad: trim (left/right: ±2), depth (up/down: ±0.05)")
    stdscr.addstr(15, 0, "Q: exit")

    try:
        stdscr.refresh()
        return stdscr.getch()  # Returns key code or -1
    except curses.error:
        return -1

def main(stdscr):
    """Main function with curses interface."""
    # Initialize curses
    curses.noecho()
    curses.cbreak()
    stdscr.keypad(True)

    pygame.init()

    controller = CarController('/dev/ttyUSB0')
    gamepad_input = GamepadInput(joystick_index=0)
    camera_input = ZEDCameraInput()

    try:
        gamepad_input.initialize()
        camera_input.initialize()
    except RuntimeError as e:
        print(f"Initialization error: {e}")
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
        while True:
            gamepad_input.get_input()
            speed, brake, steering, _, _ = gamepad_input.get_input() if is_gamepad_mode else camera_input.get_input()
            camera_input.get_input()
            controller.update(speed, brake, steering)

            # Update interface
            key = curses_interface(stdscr, controller, gamepad_input, camera_input, is_gamepad_mode)
            if key == ord('q') or (not is_gamepad_mode and cv2.waitKey(1) & 0xFF == ord('q')):
                break

    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Restore terminal
        curses.nocbreak()
        stdscr.keypad(False)
        curses.echo()
        curses.endwin()
        # Safe shutdown
        if camera_input.recording:
            camera_input.toggle_recording()
        controller.stop()
        controller.close()
        gamepad_input.close()
        camera_input.close()
        pygame.quit()
        print("Program terminated")

if __name__ == "__main__":
    curses.wrapper(main)