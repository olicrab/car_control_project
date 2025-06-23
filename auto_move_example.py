from ultralytics import YOLO
import pyzed.sl as sl
import cv2
import numpy as np
from car_controller.car_controller import CarController
import time


# Загрузка модели YOLOv8
model = YOLO("models/cone_detector.pt")  # Укажите путь к вашей модели .pt

# Цвета для классов
class_colors = {
    "Yellow": (0, 255, 255),  # Справа
    "Blue": (255, 0, 0),      # Слева
    "Orange": (0, 165, 255)   # Остановка
}

def get_box_distance(depth_data, x1, y1, x2, y2):
    # Центр бокса
    cx = int((x1 + x2) / 2)
    cy = int((y1 + y2) / 2)
    h, w = depth_data.shape
    # Область 5x5 вокруг центра, с учетом границ
    x_start = max(cx - 2, 0)
    x_end = min(cx + 3, w)
    y_start = max(cy - 2, 0)
    y_end = min(cy + 3, h)
    roi = depth_data[y_start:y_end, x_start:x_end]
    valid = roi[np.isfinite(roi) & (roi > 0)]
    if valid.size > 0:
        return float(np.median(valid))
    return None

def calculate_trajectory(blue_cones, yellow_cones, frame_width, frame_height):
    if not blue_cones or not yellow_cones:
        return None, []

    # Сортируем конусы по расстоянию (от ближнего к дальнему)
    blue_cones = sorted(blue_cones, key=lambda x: x[4] if x[4] is not None else float('inf'))
    yellow_cones = sorted(yellow_cones, key=lambda x: x[4] if x[4] is not None else float('inf'))

    # Выбираем пары конусов с близкими расстояниями
    trajectory_points = []
    min_pairs = min(len(blue_cones), len(yellow_cones), 30)  # Ограничиваем до 3 пар для плавности
    for i in range(min_pairs):
        blue_cx = (blue_cones[i][0] + blue_cones[i][2]) / 2
        yellow_cx = (yellow_cones[i][0] + yellow_cones[i][2]) / 2
        blue_cy = (blue_cones[i][1] + blue_cones[i][3]) / 2
        yellow_cy = (yellow_cones[i][1] + yellow_cones[i][3]) / 2
        # Центр полосы
        lane_cx = (blue_cx + yellow_cx) / 2
        lane_cy = (blue_cy + yellow_cy) / 2
        trajectory_points.append((int(lane_cx), int(lane_cy)))

    if not trajectory_points:
        return None, []

    # Вычисляем угол траектории на основе ближайшей точки
    nearest_point = trajectory_points[0]
    frame_center_x = frame_width / 2
    deviation = (nearest_point[0] - frame_center_x) / (frame_width / 2)  # Нормализованное отклонение [-1, 1]

    # Для змейки: учитываем направление траектории
    if len(trajectory_points) > 1:
        dx = trajectory_points[1][0] - trajectory_points[0][0]
        dy = trajectory_points[1][1] - trajectory_points[0][1]
        angle = np.arctan2(dy, dx)  # Угол в радианах
        deviation += 0.3 * np.tan(angle)  # Усиливаем поворот в зависимости от угла траектории

    return deviation, trajectory_points

def main():
    # Инициализация ZED-камеры
    zed = sl.Camera()
    init_params = sl.InitParameters()
    init_params.camera_resolution = sl.RESOLUTION.HD720
    init_params.camera_fps = 30
    init_params.depth_mode = sl.DEPTH_MODE.PERFORMANCE
    init_params.coordinate_units = sl.UNIT.METER

    if zed.open(init_params) != sl.ERROR_CODE.SUCCESS:
        print("Ошибка: не удалось инициализировать ZED-камеру")
        return

    print("ZED-камера успешно инициализирована")

    # Инициализация контроллера автомобиля
    arduino_port = "COM3"
    baud_rate = 9600
    car = CarController(arduino_port=arduino_port, baud_rate=baud_rate)
    car.set_gear("medium")

    image_zed = sl.Mat()
    depth_zed = sl.Mat()

    try:
        while True:
            if zed.grab(sl.RuntimeParameters()) == sl.ERROR_CODE.SUCCESS:
                zed.retrieve_image(image_zed, sl.VIEW.LEFT)
                zed.retrieve_measure(depth_zed, sl.MEASURE.DEPTH)
                frame = image_zed.get_data()[:, :, :3].copy()
                depth_data = depth_zed.get_data()

                # Детекция конусов
                results = model(frame)
                blue_cones = []
                yellow_cones = []
                stop = False

                for result in results:
                    boxes = result.boxes
                    for box in boxes:
                        conf = float(box.conf[0])
                        if conf < 0.8:
                            continue
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        cls = int(box.cls[0])
                        label = model.names[cls]
                        color = class_colors.get(label, (0, 255, 0))
                        distance = get_box_distance(depth_data, x1, y1, x2, y2)

                        # Рисуем маркер в центре конуса
                        cx = int((x1 + x2) / 2)
                        cy = int((y1 + y2) / 2)
                        cv2.circle(frame, (cx, cy), 5, color, -1)  # Круг радиусом 5
                        label_text = f"{distance:.2f}m" if distance is not None else "?m"
                        cv2.putText(frame, label_text, (cx + 10, cy - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

                        # Сохраняем данные о конусах
                        if label == "Blue":  # Слева
                            blue_cones.append((x1, y1, x2, y2, distance))
                        elif label == "Yellow":  # Справа
                            yellow_cones.append((x1, y1, x2, y2, distance))
                        elif label == "Orange" and distance is not None and distance < 1.0:
                            stop = True

                # Если обнаружен оранжевый конус ближе 1 метра, останавливаемся
                if stop:
                    print("Обнаружен оранжевый конус, остановка")
                    car.update(speed=0.0, brake=1.0, steering=0.0)
                    time.sleep(1)
                    car.stop()
                    break

                # Вычисляем траекторию
                deviation, trajectory_points = calculate_trajectory(blue_cones, yellow_cones, frame.shape[1], frame.shape[0])

                # Отрисовка траектории
                if trajectory_points:
                    for i in range(len(trajectory_points) - 1):
                        cv2.line(frame, trajectory_points[i], trajectory_points[i + 1], (0, 255, 0), 2)
                    # Отмечаем ближайшую точку траектории
                    cv2.circle(frame, trajectory_points[0], 8, (0, 0, 255), -1)

                # Управление машинкой
                if deviation is None:
                    print("Конусы не обнаружены, продолжаем движение прямо")
                    car.update(speed=0.3, brake=0.0, steering=0.0)
                else:
                    # Пропорциональное управление с учетом кривизны
                    steering = -deviation * 0.7  # Усиление для поворота
                    # Ограничиваем угол поворота
                    steering = max(min(steering, 1.0), -1.0)
                    # Скорость зависит от расстояния до ближайшего конуса
                    min_distance = min([c[4] for c in blue_cones + yellow_cones if c[4] is not None], default=5.0)
                    speed = 0.3 if min_distance > 2.0 else 0.2
                    print(f"Управление: скорость={speed:.2f}, угол={steering:.2f}, расстояние={min_distance:.2f}m")
                    car.update(speed=speed, brake=0.0, steering=steering)

                cv2.imshow("YOLOv8 + Trajectory (ZED)", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
            else:
                print("Ошибка: не удалось захватить кадр")
    finally:
        zed.close()
        car.stop()
        car.close()
        cv2.destroyAllWindows()
        print("ZED-камера и Arduino отключены")

if __name__ == "__main__":
    main()