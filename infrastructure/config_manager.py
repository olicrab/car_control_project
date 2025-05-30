import yaml
import os
import logging
from core.interfaces.config_manager import ConfigManager

logger = logging.getLogger(__name__)

class FileConfigManager(ConfigManager):
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self) -> dict:
        if not os.path.exists(self.config_path):
            logger.warning(f"Config file {self.config_path} not found, using defaults")
            return {
                "arduino": {"port": "/dev/ttyUSB0", "baud_rate": 9600},
                "zed": {"resolution": "HD720", "fps": 30, "depth_threshold": 0.6},
                "gamepad": {"joystick_index": 0},
                "logging": {"level": "DEBUG", "file": "logs/car_control.log"}
            }
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)

    def get_config(self) -> dict:
        return self.config

    def update_config(self, key: str, value) -> None:
        self.config[key] = value
        with open(self.config_path, 'w') as f:
            yaml.safe_dump(self.config, f)
        logger.info(f"Config updated: {key} = {value}")