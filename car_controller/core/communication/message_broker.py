from multiprocessing import Queue, Process
from typing import Any, Dict
import logging


class MessageBroker:
    def __init__(self):
        self._queues: Dict[str, Queue] = {}

    def create_queue(self, name: str) -> Queue:
        if name not in self._queues:
            self._queues[name] = Queue()
        return self._queues[name]

    def get_queue(self, name: str) -> Queue:
        return self._queues[name]