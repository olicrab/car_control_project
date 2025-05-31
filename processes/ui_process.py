from multiprocessing import Process, Event
import curses
import logging
from application.state_manager import StateManager

logger = logging.getLogger(__name__)

class UIProcess(Process):
    def __init__(self, state_manager: StateManager, stop_event: Event):
        super().__init__()
        self.state_manager = state_manager
        self.stop_event = stop_event
        logger.info("UIProcess initialized")

    def run(self) -> None:
        logger.info("UI process started")
        try:
            curses.wrapper(self._run_ui)
        except Exception as e:
            logger.error(f"UI process error: {e}")
            self.state_manager.update_state(last_error=f"UI process error: {e}")

    def _run_ui(self, stdscr) -> None:
        curses.curs_set(0)
        stdscr.timeout(50)
        while not self.stop_event.is_set():
            try:
                state = self.state_manager.get_state()
                stdscr.clear()
                stdscr.addstr(0, 0, "Car Control", curses.A_BOLD)
                stdscr.addstr(2, 0, f"Mode: {state['mode']}")
                stdscr.addstr(3, 0, f"Speed: {state.get('motor_value', 90)}")
                stdscr.addstr(4, 0, f"Gear: {state['gear']}")
                stdscr.addstr(5, 0, f"Steering: {state.get('steering_value', 90)}")
                stdscr.addstr(6, 0, f"Trim: {state['trim']:.3f}")
                stdscr.addstr(7, 0, f"Depth Threshold: {state['depth_threshold']:.2f} m")
                stdscr.addstr(8, 0, f"Min Distance: {state['min_distance']:.2f} m")
                stdscr.addstr(9, 0, f"Recording: {'On' if state.get('recording', False) else 'Off'}")
                stdscr.addstr(10, 0, f"Braking: {'On' if state['braking'] else 'Off'}")
                stdscr.addstr(12, 0, f"Last Error: {state['last_error'] or 'None'}")
                stdscr.addstr(14, 0, "Left Stick: steering, Triggers: throttle/brake, Bumpers: gears")
                stdscr.addstr(15, 0, "Start: mode, A: record, B: reverse, X: reset trim, Y: reset depth")
                stdscr.addstr(16, 0, "D-Pad: trim (left/right: ±2), depth (up/down: ±0.05)")
                stdscr.addstr(17, 0, "Q: exit")
                stdscr.refresh()
                if stdscr.getch() == ord('q'):
                    self.stop_event.set()
            except curses.error as e:
                logger.error(f"Curses refresh error: {e}")
                self.state_manager.update_state(last_error=f"Curses refresh error: {e}")
            except Exception as e:
                logger.error(f"UI update error: {e}")
                self.state_manager.update_state(last_error=f"UI update error: {e}")