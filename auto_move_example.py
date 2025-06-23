from ultralytics import YOLO
import pyzed.sl as sl
import cv2
import numpy as np
from car_controller.car_controller import CarController
import time
import math

# Загрузка модели YOLOv8
model = YOLO("models/cone_detector.pt")

# Цвета для классов
class_colors = {
    "Yellow": (0, 255, 255),  # Справа
    "Blue": (255, 0, 0),  # Слева
    "Orange": (0, 165, 255)  # Остановка
}

# Глобальные параметры
WINDOW_SIZE = [1280, 720]
CURRENT_POS = (WINDOW_SIZE[0] // 2, WINDOW_SIZE[1] - 10)  # Позиция машинки чуть выше нижнего края
CURRENT_HEADING = -math.pi / 2  # Направление вверх
BASE_LOOKAHEAD_DISTANCE = 10  # Базовое расстояние в пикселях (~2 м, калибровать)
FILTER_SIZE = 3  # Увеличено для сглаживания
KP_STEERING = 0.4  # Чувствительность руления
MAX_TURN_ANGLE = math.radians(30)
MIN_ZEROING_ANGLE = math.radians(4)
BASE_SPEED = 0.5  # Диапазон [0, 1] для CarController
MIN_SPEED = 0.1
BRAKE_ASPECT = 0.7  # Увеличено для замедления на поворотах
ORANGE_STOP_DISTANCE = 1.0  # Метры


def get_box_distance(depth_data, x1, y1, x2, y2):
    cx = int((x1 + x2) / 2)
    cy = int((y1 + y2) / 2)
    h, w = depth_data.shape
    x_start = max(cx - 2, 0)
    x_end = min(cx + 3, w)
    y_start = max(cy - 2, 0)
    y_end = min(cy + 3, h)
    roi = depth_data[y_start:y_end, x_start:x_end]
    valid = roi[np.isfinite(roi) & (roi > 0)]
    if valid.size > 0:
        return float(np.median(valid))
    return None


def smooth_path(points, filter_size=FILTER_SIZE):
    if not points or len(points) < 2:
        return points
    smoothed = []
    for i in range(len(points)):
        start = max(0, i - filter_size // 2)
        end = min(len(points), i + filter_size // 2 + 1)
        avg_x = np.mean([p[0] for p in points[start:end]])
        avg_y = np.mean([p[1] for p in points[start:end]])
        smoothed.append((avg_x, avg_y))
    return smoothed


def pair_cones(blue_cones, yellow_cones):
    # Сортируем по расстоянию
    blue_cones = sorted(blue_cones, key=lambda x: x[2] if x[2] is not None else float('inf'))
    yellow_cones = sorted(yellow_cones, key=lambda x: x[2] if x[2] is not None else float('inf'))

    # Парное соответствие по близости расстояний
    paired = []
    min_pairs = min(len(blue_cones), len(yellow_cones))
    for i in range(min_pairs):
        blue = blue_cones[i]
        yellow = yellow_cones[i]
        center_x = (blue[0] + yellow[0]) / 2
        center_y = (blue[1] + yellow[1]) / 2
        avg_distance = (blue[2] + yellow[2]) / 2 if blue[2] is not None and yellow[2] is not None else None
        paired.append((center_x, center_y, avg_distance))

    # Если одной стороны не хватает, используем противоположную границу
    if not blue_cones and yellow_cones:
        for y in yellow_cones[:3]:
            center_x = (0 + y[0]) / 2
            center_y = y[1]
            paired.append((center_x, center_y, y[2]))
    elif not yellow_cones and blue_cones:
        for b in blue_cones[:3]:
            center_x = (b[0] + WINDOW_SIZE[0]) / 2
            center_y = b[1]
            paired.append((center_x, center_y, b[2]))

    # Сортируем по расстоянию
    paired = sorted(paired, key=lambda x: x[2] if x[2] is not None else float('inf'))
    return [(p[0], p[1]) for p in paired]


def pure_pursuit_steering(current_pos, current_heading, path, lookahead_distance):
    # Находим ближайшую точку на траектории
    if not path:
        return 0.0, current_pos
    distances = [math.sqrt((p[0] - current_pos[0]) ** 2 + (p[1] - current_pos[1]) ** 2) for p in path]
    closest_idx = np.argmin(distances)

    # Ищем целевую точку на lookahead_distance
    target_point = path[closest_idx]
    for i in range(closest_idx, len(path)):
        dist = math.sqrt((path[i][0] - current_pos[0]) ** 2 + (path[i][1] - current_pos[1]) ** 2)
        if dist >= lookahead_distance:
            target_point = path[i]
            break

    # Вычисляем угол поворота (Pure Pursuit)
    dx = target_point[0] - current_pos[0]
    dy = target_point[1] - current_pos[1]
    angle_to_target = math.atan2(dy, dx)
    steering_angle = angle_to_target - current_heading
    steering_angle = (steering_angle + math.pi) % (2 * math.pi) - math.pi
    final_angle = max(-MAX_TURN_ANGLE, min(MAX_TURN_ANGLE, KP_STEERING * steering_angle))
    if abs(final_angle) < MIN_ZEROING_ANGLE:
        final_angle = 0

    return final_angle, target_point


def adjust_speed(steering_angle, min_distance):
    speed = BASE_SPEED * (1 - (abs(steering_angle) / MAX_TURN_ANGLE) ** BRAKE_ASPECT)
    if min_distance is not None and min_distance < 2.0:
        speed *= max(0.5, min_distance / 2.0)  # Замедляемся при близких конусах
    return max(MIN_SPEED, speed)


def interpolate_color(distance, max_distance=150):
    normalized_distance = min(distance / max_distance, 1)
    red = int(255 * normalized_distance)
    green = int(255 * (1 - normalized_distance))
    return (0, green, red)


def draw_colored_path(frame, path):
    if len(path) < 2:
        return frame
    for i in range(1, len(path)):
        p1 = path[i - 1]
        p2 = path[i]
        distance = math.sqrt((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2)
        color = interpolate_color(distance)
        cv2.line(frame, (int(p1[0]), int(p1[1])), (int(p2[0]), int(p2[1])), color, 2)
    return frame


def main():
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
                min_distance = float('inf')

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

                        cx = (x1 + x2) / 2
                        cy = (y1 + y2) / 2
                        cv2.circle(frame, (int(cx), int(cy)), 5, color, -1)
                        label_text = f"{distance:.2f}m" if distance is not None else "?m"
                        cv2.putText(frame, label_text, (int(cx) + 10, int(cy) - 10),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

                        if distance is not None and distance < min_distance:
                            min_distance = distance

                        if label == "Blue":
                            blue_cones.append((cx, cy, distance))
                        elif label == "Yellow":
                            yellow_cones.append((cx, cy, distance))
                        elif label == "Orange" and distance is not None and distance < ORANGE_STOP_DISTANCE:
                            stop = True

                if stop:
                    print("Обнаружен оранжевый конус, остановка")
                    car.update(speed=0.0, brake=1.0, steering=0.0)
                    time.sleep(1)
                    car.stop()
                    break

                # Формируем траекторию
                center_line = pair_cones(blue_cones, yellow_cones)
                center_line = smooth_path(center_line)

                # Динамическая настройка lookahead_distance
                lookahead_distance = BASE_LOOKAHEAD_DISTANCE * (min_distance / 3.0 if min_distance is not None else 1.0)
                lookahead_distance = max(50, min(lookahead_distance, 200))

                # Вычисляем угол поворота (Pure Pursuit)
                steering_angle, target_point = pure_pursuit_steering(CURRENT_POS, CURRENT_HEADING, center_line,
                                                                     lookahead_distance)
                speed = adjust_speed(steering_angle, min_distance)

                # Отрисовка
                if center_line:
                    draw_colored_path(frame, center_line)
                cv2.circle(frame, (int(target_point[0]), int(target_point[1])), 8, (0, 0, 255), -1)
                cv2.circle(frame, (int(CURRENT_POS[0]), int(CURRENT_POS[1])), 10, (255, 255, 255), 2)

                # Управление
                if not center_line:
                    print("Конусы не обнаружены, движение прямо")
                    car.update(speed=BASE_SPEED, brake=0.0, steering=0.0)
                else:
                    steering = steering_angle / MAX_TURN_ANGLE
                    steering = max(min(steering, 1.0), -1.0)
                    print(f"Управление: скорость={speed:.2f}, угол={steering:.2f}, расстояние={min_distance:.2f}m")
                    car.update(speed=speed, brake=0.0, steering=steering)

                cv2.imshow("YOLOv8 + Trajectory (ZED)", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
            else:
                print("Ошибка: не удалось захватить кадр")
    finally:
        zed.close()
        car.close()
        cv2.destroyAllWindows()
        print("ZED-камера и Arduino отключены")


if __name__ == "__main__":
    main()