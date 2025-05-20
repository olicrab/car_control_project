import sys
import time
import pyzed.sl as sl

# Инициализация камеры
init_params = sl.InitParameters()
init_params.camera_resolution = sl.RESOLUTION.HD1080
init_params.camera_fps = 30

zed = sl.Camera()
err = zed.open(init_params)
if err != sl.ERROR_CODE.SUCCESS:
    print("Не удалось открыть камеру ZED")
    sys.exit(1)

print("Камера успешно подключена")

# Захват изображения
while True:
    if zed.grab() == sl.ERROR_CODE.SUCCESS:
        print("Кадр получен")
        time.sleep(0.1)  # Пауза между кадрами

# Закрытие камеры
zed.close()
