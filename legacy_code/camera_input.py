import cv2
import time
import os
from .input_device import InputDevice
from typing import Tuple

class CameraInput(InputDevice):
    def __init__(self, device: int = 0):
        self.device = device
        self.cap = None
        self.window_name = "Camera Feed"
        self.recording = False
        self.out = None
        self.output_dir = os.path.dirname(__file__)  # Директория проекта
        self.output_path = self._generate_output_path()
        self.show_window = False
        self.window_created = False

    def _generate_output_path(self) -> str:
        """Генерирует уникальный путь для сохранения видео."""
        timestamp = int(time.time())
        return os.path.join(self.output_dir, f"output_{timestamp}.avi")

    def initialize(self) -> None:
        """Инициализирует камеру с использованием V4L2 и формата YUYV."""
        self.close()

        max_attempts = 3
        for attempt in range(max_attempts):
            self.cap = cv2.VideoCapture(self.device, cv2.CAP_V4L2)
            if self.cap.isOpened():
                break
            print(f"Попытка {attempt + 1}/{max_attempts}: Не удалось открыть камеру")
            time.sleep(0.5)
        else:
            raise RuntimeError("Ошибка: Не удалось открыть камеру после нескольких попыток")

        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"YUYV"))
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        width = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        height = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        fps = self.cap.get(cv2.CAP_PROP_FPS) or 20.0  # Устанавливаем FPS по умолчанию
        fourcc = int(self.cap.get(cv2.CAP_PROP_FOURCC)).to_bytes(4, 'little').decode('ascii', errors='ignore')
        print(f"Камера инициализирована. Разрешение: {width}x{height}, FPS: {fps}, Формат: {fourcc}")

    def toggle_recording(self) -> None:
        """Запускает или останавливает запись видео."""
        if not self.recording:
            if not self.cap or not self.cap.isOpened():
                print("Ошибка: Камера не инициализирована, запись невозможна")
                return

            # Проверяем права на запись
            if not os.access(self.output_dir, os.W_OK):
                print(f"Ошибка: Нет прав на запись в директорию {self.output_dir}")
                return

            width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = self.cap.get(cv2.CAP_PROP_FPS) or 20.0
            codecs = ['XVID', 'MJPG', 'H264', 'DIVX']  # Расширяем список кодеков
            for codec in codecs:
                fourcc = cv2.VideoWriter_fourcc(*codec)
                self.out = cv2.VideoWriter(self.output_path, fourcc, fps, (width, height))
                if self.out.isOpened():
                    print(f"VideoWriter открыт с кодеком {codec}, путь: {self.output_path}")
                    break
                print(f"Предупреждение: Кодек {codec} не сработал, пробуем другой")
            else:
                print("Ошибка: Не удалось инициализировать VideoWriter с доступными кодеками")
                self.out = None
                return

            self.recording = True
            print(f"Запись начата: {self.output_path}")
        else:
            if self.out is not None and self.out.isOpened():
                self.out.release()
                print("VideoWriter закрыт")
            self.out = None
            self.recording = False
            if os.path.exists(self.output_path) and os.path.getsize(self.output_path) > 0:
                print(f"Запись сохранена: {self.output_path}, размер: {os.path.getsize(self.output_path)} байт")
            else:
                print(f"Ошибка: Файл записи пуст или не создан: {self.output_path}")
            self.output_path = self._generate_output_path()  # Новый путь для следующей записи

    def get_input(self) -> Tuple[float, float, float, bool, bool]:
        """Получает кадр и возвращает команды управления или пишет кадр, если включена запись."""
        if not self.cap or not self.cap.isOpened():
            print("Ошибка: Камера не инициализирована")
            return 0.0, 0.0, 0.0, False, False

        ret, frame = self.cap.read()
        if not ret or frame is None:
            print("Ошибка: Не удалось захватить кадр")
            return 0.0, 0.0, 0.0, False, False

        # Записываем кадр, если включена запись
        if self.recording and self.out is not None and self.out.isOpened():
            self.out.write(frame)
            print(f"Кадр записан: {frame.shape}, путь: {self.output_path}")  # Отладка

        # Показываем кадр, если окно активно
        if self.show_window and self.window_created:
            cv2.imshow(self.window_name, frame)
            cv2.waitKey(1)

        # Возвращаем команды только в режиме автопилота
        gas, brake, steering = self.process_frame(frame) if not self.show_window else (0.0, 0.0, 0.0)
        return gas, brake, steering, False, False

    def set_window_visible(self, visible: bool) -> None:
        """Управляет отображением окна камеры."""
        self.show_window = visible
        if visible and self.cap and self.cap.isOpened():
            if not self.window_created:
                width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
                cv2.resizeWindow(self.window_name, width, height)
                self.window_created = True
        elif not visible and self.window_created:
            try:
                cv2.destroyWindow(self.window_name)
                self.window_created = False
            except cv2.error:
                pass

    def process_frame(self, frame):
        """Обрабатывает кадр для получения команд управления."""
        # Заглушка: здесь будет логика компьютерного зрения
        return 0.0, 0.0, 0.0

    def close(self) -> None:
        """Закрывает камеру и освобождает ресурсы."""
        if self.recording:
            self.toggle_recording()  # Завершаем запись корректно
        if self.cap is not None:
            time.sleep(0.1)
            self.cap.release()
            self.cap = None
        if self.window_created:
            try:
                cv2.destroyWindow(self.window_name)
                self.window_created = False
            except cv2.error:
                pass
        print("Камера закрыта.")