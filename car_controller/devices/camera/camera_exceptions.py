class CameraException(Exception):
    """Базовый класс для исключений камеры"""
    pass

class CameraInitializationError(CameraException):
    """Ошибка инициализации камеры"""
    pass

class CameraFrameError(CameraException):
    """Ошибка получения кадра"""
    pass