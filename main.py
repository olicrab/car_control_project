import logging.config
import yaml
import os
from multiprocessing import Queue, Event
from processes.process_manager import ProcessManager
from processes.input_process import InputProcess
from processes.command_process import CommandProcess
from processes.arduino_process import ArduinoProcess
from processes.ui_process import UIProcess
from application.input_manager import InputManager
from application.car_controller import CarController
from application.command_processor import CommandProcessor
from application.state_manager import StateManager
from infrastructure.zed_camera import ZEDCameraInput
from infrastructure.gamepad import GamepadInput
from infrastructure.arduino import ArduinoAdapter
from infrastructure.video_recorder import ZEDVideoRecorder
from infrastructure.config_manager import FileConfigManager

def setup_logging():
    try:
        with open('config/logging_config.yaml', 'r') as f:
            logging.config.dictConfig(yaml.safe_load(f))
        logger = logging.getLogger(__name__)
        logger.debug("Logging configured successfully")
    except Exception as e:
        print(f"Error configuring logging: {e}")
        # Настраиваем базовое логирование в случае ошибки
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            handlers=[
                logging.handlers.RotatingFileHandler('logs/car_control.log', maxBytes=5242880, backupCount=3),
                logging.StreamHandler()
            ]
        )
        logger = logging.getLogger(__name__)
        logger.error(f"Fallback logging configured due to error: {e}")

def main():
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Starting car control system")

    config_manager = FileConfigManager('config/config.yaml')
    config = config_manager.get_config()

    state_manager = StateManager()
    video_recorder = ZEDVideoRecorder(config['zed']['output_dir'], state_manager)
    zed_camera = ZEDCameraInput(video_recorder, state_manager)
    gamepad = GamepadInput(config['gamepad']['joystick_index'], state_manager)
    arduino = ArduinoAdapter(config['arduino']['port'], config['arduino']['baud_rate'])

    input_manager = InputManager(state_manager)
    input_manager.register_device("gamepad", gamepad)
    input_manager.register_device("zed", zed_camera)

    car_controller = CarController(arduino, state_manager)
    command_queue = Queue()
    arduino_queue = Queue()
    stop_event = Event()

    def toggle_input_mode():
        input_manager.toggle_mode()
        zed_camera.set_window_visible(input_manager.current_mode == "zed")
        logger.info(f"Mode switched to: {input_manager.current_mode}")

    def set_reverse_gear():
        state_manager.update_state(gear="reverse")
        logger.info("Reverse gear set")

    gamepad.register_button_action(5, car_controller.increase_gear)  # RB
    gamepad.register_button_action(4, car_controller.decrease_gear)  # LB
    gamepad.register_button_action(7, toggle_input_mode)  # Start
    gamepad.register_button_action(0, video_recorder.toggle_recording)  # A
    gamepad.register_button_action(1, set_reverse_gear)  # B
    gamepad.register_button_action(2, lambda: gamepad.set_steering_trim(0.0))  # X
    gamepad.register_button_action(3, lambda: state_manager.update_state(depth_threshold=0.6))  # Y

    input_process = InputProcess(input_manager, command_queue, stop_event)
    command_process = CommandProcess(CommandProcessor(input_manager, car_controller, command_queue), stop_event)
    arduino_process = ArduinoProcess(arduino, arduino_queue, stop_event)
    ui_process = UIProcess(state_manager, stop_event)

    process_manager = ProcessManager(input_process, command_process, arduino_process, ui_process)

    try:
        process_manager.start()
        logger.debug("Main loop started")
        while not stop_event.is_set():
            pass
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
        stop_event.set()
    except Exception as e:
        logger.error(f"Main loop error: {e}")
        state_manager.update_state(last_error=f"Main loop error: {e}")
    finally:
        process_manager.stop()
        logger.info("System shutdown complete")

if __name__ == "__main__":
    main()