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

    def run(self) -> None:
        logger.info("UI process started")
        curses.wrapper(self._run_ui)

    def _run_ui(self, stdscr) -> None:
        curses.curs_set(0)
        stdscr.timeout(50)
        while not self.stop_event.is_set():
            state = self.state_manager.get_state()
            stdscr.clear()
            stdscr.addstr(0, 0, "Car Control", curses.A_BOLD)
            stdscr.addstr(2, 0, f"Mode: {state['mode']}")
            stdscr.addstr(4, 0, f"Speed: {state.get('motor_value', 90)}")
            stdscr.addstr(5, 0, f"Gear: {state['gear']}")
            stdscr.addstr(6, 0, f"Steering: {state.get('steering_value', 90)}")
            stdscr.addstr(7, 0, f"Trim: {state['trim']:.3f}")
            stdscr.addstr(8, 0, f"Depth Threshold: {state['depth_threshold']:.2f} m")
            stdscr.addstr(9, 0, f"Min Distance: {state['min_distance']:.2f} m")
            stdscr.addstr(10, 0, f"Recording: {'On' if state['recording'] else 'Off'}")
            stdscr.addstr(11, 0, f"Braking: {'On' if state['braking'] else 'Off'}")
            stdscr.addstr(13, 0, f"Last Error: {state['last_error'] or 'None'}")
            try:
                stdscr.refresh()
                if stdscr.getch() == ord('q'):
                    self.stop_event.set()
            except curses.error:
                logger.error("Curses refresh error")