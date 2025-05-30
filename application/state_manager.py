from multiprocessing import Manager
from typing import Dict

class StateManager:
    def __init__(self):
        self.manager = Manager()
        self.state = self.manager.dict({
            "gear": "turtle",
            "mode": "gamepad",
            "trim": 0.0,
            "depth_threshold": 0.6,
            "recording": False,
            "min_distance": float('inf'),
            "braking": False,
            "last_error": ""
        })

    def update_state(self, **kwargs) -> None:
        for key, value in kwargs.items():
            if value is not None:
                self.state[key] = value

    def get_state(self) -> Dict:
        return dict(self.state)