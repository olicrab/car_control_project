from abc import ABC, abstractmethod

class VideoRecorder(ABC):
    @abstractmethod
    def toggle_recording(self) -> None:
        pass

    @abstractmethod
    def record_frame(self, frame) -> None:
        pass

    @abstractmethod
    def initialize(self) -> None:
        pass

    @abstractmethod
    def close(self) -> None:
        pass