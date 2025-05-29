from multiprocessing import Process

from ..core.config.settings import Settings
from ..core.logging import setup_logger
from ..core.communication import MessageBroker, CameraFrame, ControlCommand
from ..devices.input import Gamepad
from typing import Tuple


class ControlProcess(Process):
    def __init__(self, broker: MessageBroker, settings: Settings):
        super().__init__()
        self.frame_queue = broker.get_queue('camera_frames')
        self.command_queue = broker.create_queue('control_commands')
        self.gamepad = Gamepad()
        self.settings = settings
        self.logger = setup_logger(__name__)

    def process_input(self, frame: CameraFrame,
                      gamepad_input: Tuple[float, float, float, bool, bool]) -> ControlCommand:
        speed, brake, steering, emergency_stop, recording = gamepad_input

        # Если активирован emergency_stop, игнорируем все входные данные
        if emergency_stop:
            return ControlCommand(speed=0.0, brake=1.0, steering=0.0, timestamp=frame.timestamp)

        return ControlCommand(
            speed=speed,
            brake=brake,
            steering=steering,
            timestamp=frame.timestamp
        )

    def run(self):
        try:
            self.gamepad.initialize()
            while True:
                try:
                    frame = self.frame_queue.get()
                    gamepad_input = self.gamepad.get_input()
                    command = self.process_input(frame, gamepad_input)
                    self.command_queue.put(command)
                except Exception as e:
                    self.logger.error(f"Error processing control: {e}")
        except Exception as e:
            self.logger.error(f"Control process error: {e}")
        finally:
            self.gamepad.close()
