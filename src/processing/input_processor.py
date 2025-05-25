import multiprocessing
from src.core.control_modes import ControlMode, ManualControlStrategy, AutopilotControlStrategy

class InputProcessor:
    def __init__(self, input_queue, output_queue, camera_processor):
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.control_mode = ControlMode.MANUAL

        self.manual_strategy = ManualControlStrategy()
        self.autopilot_strategy = AutopilotControlStrategy(camera_processor)

    def process(self):
        while True:
            if not self.input_queue.empty():
                input_data = self.input_queue.get()

                if self.control_mode == ControlMode.MANUAL:
                    processed_input = self.manual_strategy.process_input(input_data)
                elif self.control_mode == ControlMode.AUTOPILOT:
                    processed_input = self.autopilot_strategy.process_input(input_data)

                self.output_queue.put(processed_input)

    def toggle_control_mode(self):
        if self.control_mode == ControlMode.MANUAL:
            self.control_mode = ControlMode.AUTOPILOT
        else:
            self.control_mode = ControlMode.MANUAL