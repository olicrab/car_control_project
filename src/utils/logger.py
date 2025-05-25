import logging
import os
from datetime import datetime


class Logger:
    def __init__(self, name='CarControlLogger'):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)

        # Создание директории для логов
        log_dir = 'logs'
        os.makedirs(log_dir, exist_ok=True)

        # Файловый логгер
        log_file = os.path.join(log_dir, f'{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)

        # Консольный логгер
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # Форматирование
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # Добавление хендлеров
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def debug(self, message):
        self.logger.debug(message)

    def info(self, message):
        self.logger.info(message)

    def warning(self, message):
        self.logger.warning(message)

    def error(self, message):
        self.logger.error(message)

    def critical(self, message):
        self.logger.critical(message)
