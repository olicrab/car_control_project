import logging.config
import yaml
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
    with open('config/logging_config.yaml', 'r') as f:
        logging.config.dictConfig(yaml.safe_load(f))

def main():
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Starting car control system")

    config_manager = FileConfigManager('config/config.yaml')
    config = config_manager.get_config()

    state_manager = StateManager()
    video_recorder = ZEDVideoRecorder(config['zed']['output_dir'])
    zed_camera = ZEDCameraInput(video_recorder)
    gamepad = GamepadInput(config['gamepad']['joystick_index'])
    arduino = ArduinoAdapter(config['arduino']['port'], config['arduino']['baud_rate'])

    input_manager = InputManager(state_manager)
    input_manager.register_device("gamepad", gamepad)
    input_manager.register_device("zed", zed_camera)

    car_controller = CarController(arduino, state_manager)
    command_queue = Queue()
    stop_event = Event()

    input_process = InputProcess(input_manager, command_queue, stop_event)
    command_process = CommandProcess(CommandProcessor(input_manager, car_controller, command_queue), stop_event)
    arduino_process = ArduinoProcess(arduino, Queue(), stop_event)
    ui_process = UIProcess(state_manager, stop_event)

    process_manager = ProcessManager(input_process, command_process, arduino_process, ui_process)

    try:
        process_manager.start()
        while not stop_event.is_set():
            pass
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    finally:
        process_manager.stop()
        logger.info("System shutdown complete")

if __name__ == "__main__":
    main()