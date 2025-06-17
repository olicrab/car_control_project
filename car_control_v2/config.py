import os
from dataclasses import dataclass
from typing import Dict, Any, Optional

@dataclass
class CameraConfig:
    """Конфигурация камеры ZED."""
    fps: int = 30
    depth_mode: str = "PERFORMANCE"
    depth_threshold: float = 1.0
    depth_step: float = 0.1
    roi_size: float = 0.3
    default_speed: float = 0.5
    output_dir: str = "recordings"

@dataclass
class GamepadConfig:
    """Конфигурация геймпада."""
    deadzone: float = 0.1
    max_speed: float = 1.0
    max_steering: float = 1.0

@dataclass
class ArduinoConfig:
    port: str = '/dev/ttyUSB0'
    baud_rate: int = 9600
    neutral_motor_value: int = 90
    gears: Dict[str, Dict[str, Any]] = None

    def __post_init__(self):
        if self.gears is None:
            self.gears = {
                "turtle": {"max_speed": 15, "direction": "forward"},
                "slow": {"max_speed": 30, "direction": "forward"},
                "medium": {"max_speed": 50, "direction": "forward"},
                "fast": {"max_speed": 100, "direction": "forward"}
            }

@dataclass
class LoggingConfig:
    level: str = "DEBUG"
    format: str = '%(asctime)s [%(levelname)s] %(message)s'
    log_file: str = 'car_control.log'
    max_bytes: int = 5 * 1024 * 1024  # 5 MB
    backup_count: int = 3

@dataclass
class Config:
    """Основная конфигурация проекта."""
    camera: CameraConfig = CameraConfig()
    gamepad: GamepadConfig = GamepadConfig()
    arduino: ArduinoConfig = ArduinoConfig()
    logging: LoggingConfig = LoggingConfig()
    serial_port: Optional[str] = None
    baud_rate: int = 115200
    debug: bool = False
    
    # Пути для сохранения данных
    output_dir: str = os.path.join(os.path.dirname(__file__), "output")
    
    def __post_init__(self):
        # Создаем директорию для выходных файлов, если она не существует
        os.makedirs(self.output_dir, exist_ok=True) 