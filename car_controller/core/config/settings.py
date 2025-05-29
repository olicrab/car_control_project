from dataclasses import dataclass

@dataclass
class CameraSettings:
    depth_threshold: float = 2.0
    depth_step: float = 0.1
    show_window: bool = True

@dataclass
class ArduinoSettings:
    port: str = '/dev/ttyUSB0'
    baudrate: int = 9600

@dataclass
class Settings:
    camera: CameraSettings = CameraSettings()
    arduino: ArduinoSettings = ArduinoSettings()
    recording_enabled: bool = True
    debug_mode: bool = True