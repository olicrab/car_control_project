"""Простой пример работы с ZED-камерой: получение карты глубины, вывод
минимальной дистанции до объектов и отображение карты глубины."""

import pyzed.sl as sl
import cv2
import numpy as np


def main():
    # Инициализация ZED-камеры
    zed = sl.Camera()
    init_params = sl.InitParameters()
    init_params.camera_resolution = sl.RESOLUTION.HD720
    init_params.camera_fps = 30
    # init_params.depth_mode = sl.DEPTH_MODE.PERFORMANCE
    init_params.depth_mode = sl.DEPTH_MODE.ULTRA
    # init_params.depth_mode = sl.DEPTH_MODE.NEURAL
    # init_params.depth_mode = sl.DEPTH_MODE.NEURAL_PLUS
    # init_params.depth_mode = sl.DEPTH_MODE.LAST
    init_params.coordinate_units = sl.UNIT.METER

    if zed.open(init_params) != sl.ERROR_CODE.SUCCESS:
        print("Ошибка: не удалось инициализировать ZED-камеру")
        return

    print("ZED-камера успешно инициализирована")

    runtime_params = sl.RuntimeParameters()
    depth_zed = sl.Mat()

    try:
        while True:
            # Захват кадра
            if zed.grab(runtime_params) == sl.ERROR_CODE.SUCCESS:
                # Получение карты глубины
                zed.retrieve_measure(depth_zed, sl.MEASURE.DEPTH)
                depth_data = depth_zed.get_data()

                # Вычисление минимального расстояния до объекта
                valid_depth = depth_data[np.isfinite(depth_data) & (depth_data > 0)]
                if valid_depth.size > 0:
                    min_distance = np.min(valid_depth)
                    print(f"Минимальное расстояние до объекта: {min_distance:.2f} м")
                else:
                    print("Нет данных о расстоянии")

                # Нормализация карты глубины для отображения
                depth_display = depth_data.copy()
                depth_display[np.isinf(depth_display)] = 0
                depth_display = cv2.normalize(depth_display, None, 0, 255, cv2.NORM_MINMAX, cv2.CV_8U)

                # Отображение карты глубины
                cv2.imshow("Depth Map", depth_display)

                # Выход по нажатию клавиши 'q'
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            else:
                print("Ошибка: не удалось захватить кадр")
    finally:
        # Закрытие камеры и окон
        zed.close()
        cv2.destroyAllWindows()
        print("ZED-камера отключена")

if __name__ == "__main__":
    main()
