import logging
import logging.handlers
import os


def setup_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    if not os.path.exists('logs'):
        os.makedirs('logs')

    file_handler = logging.handlers.RotatingFileHandler(
        'logs/car_control.log',
        maxBytes=5 * 1024 * 1024,
        backupCount=3
    )

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger