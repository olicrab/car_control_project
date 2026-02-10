"""Пример полуавтоматического движения автомобиля: ZED-камера и модель YOLO
обнаруживают конусы и строят траекторию, а CarController управляет машиной
по рассчитанной траектории."""

import pyzed.sl as sl
import cv2
import numpy as np
from ultralytics import YOLO
from car_controller.car_controller import CarController
import math
import time
import os

# Путь к модели
MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "cone_detector.engine")
if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(f"Модель не найдена: {MODEL_PATH}")
model = YOLO(MODEL_PATH)

# Константы
WINDOW_SIZE = (1280, 720)
CURRENT_POS = (WINDOW_SIZE[0] // 2, WINDOW_SIZE[1] - 50)
CURRENT_HEADING = -math.pi / 2
BASE_SPEED = 0.95  # Скорость 0–1, масштабируется в CarController
MIN_SPEED = 0.9
MAX_TURN_ANGLE = math.radians(30)
ORANGE_STOP_DISTANCE = 0.4  # м
LOOKAHEAD_DISTANCE = 150  # пиксели
KP_STEERING = 0.8
CONF_THRESHOLD = 0.5
FILTER_SIZE = 3

# Цвета
COLORS = {
    "Yellow": (0, 255, 255),
    "Blue": (255, 0, 0),
    "Orange": (0, 165, 255)
}

def get_cone_distance(depth_data, box, cx, cy):
    """Получение расстояния до конуса."""
    h, w = depth_data.shape
    roi = depth_data[max(cy - 5, 0):min(cy + 6, h), max(cx - 5, 0):min(cx + 6, w)]
    valid = roi[np.isfinite(roi) & (roi > 0)]
    return float(np.median(valid)) if valid.size > 4 else None  # Минимум 4 валидных пикселя

def correct_cone_coordinates(cx, cy, depth, camera_params):
    """Коррекция координат конуса для центральной перспективы."""
    if depth is None or depth <= 0:
        return cx, cy
    try:
        fx = camera_params.left_cam.fx
        baseline = camera_params.stereo_transform.get_translation().tx  # Базовая линия (м)
        disparity = baseline * fx / depth
        cx_corrected = cx - disparity / 2  # Смещение к центру стереопары
        return cx_corrected, cy
    except AttributeError:
        print("Ошибка: некорректные параметры калибровки, используются исходные координаты")
        return cx, cy

def detect_cones(frame, depth_data, camera_params):
    """Обнаружение и классификация конусов с коррекцией координат."""
    results = model(frame)
    blue_cones, yellow_cones, orange_cones = [], [], []
    min_distance = float('inf')

    for result in results:
        for box in result.boxes:
            if float(box.conf[0]) < CONF_THRESHOLD:
                continue
            label = model.names[int(box.cls[0])]
            x1, y1, x2, y2 = map(int, box.xyxy[0].cpu().numpy())
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
            distance = get_cone_distance(depth_data, box, cx, cy)
            cx, cy = correct_cone_coordinates(cx, cy, distance, camera_params)

            color = COLORS.get(label, (0, 255, 0))
            cv2.circle(frame, (int(cx), int(cy)), 5, color, -1)
            cv2.putText(frame, f"{distance:.2f}m" if distance else "?m",
                        (int(cx) + 10, int(cy) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

            if distance and distance < min_distance:
                min_distance = distance

            if label == "Blue":
                blue_cones.append((cx, cy))
            elif label == "Yellow":
                yellow_cones.append((cx, cy))
            elif label == "Orange":
                orange_cones.append((cx, cy, distance))

    return blue_cones, yellow_cones, orange_cones, min_distance

def smooth_path(cones):
    """Сглаживание координат конусов."""
    if len(cones) < 2:
        return cones
    smoothed = []
    for i in range(len(cones)):
        start = max(0, i - FILTER_SIZE // 2)
        end = min(len(cones), i + FILTER_SIZE // 2 + 1)
        avg_x = np.mean([cone[0] for cone in cones[start:end]])
        avg_y = np.mean([cone[1] for cone in cones[start:end]])
        smoothed.append((int(avg_x), int(avg_y)))
    return smoothed

def balance_cones(blue_cones, yellow_cones):
    """Балансировка конусов."""
    if not blue_cones and yellow_cones:
        blue_cones = [(0, y) for _, y in yellow_cones]
    elif not yellow_cones and blue_cones:
        yellow_cones = [(WINDOW_SIZE[0], y) for _, y in blue_cones]
    return blue_cones, yellow_cones

def calculate_center_line(blue_cones, yellow_cones):
    """Построение центральной линии."""
    return [( (b[0] + y[0]) / 2, (b[1] + y[1]) / 2 ) for b, y in zip(blue_cones, yellow_cones)]

def find_target_point(center_line, current_pos):
    """Поиск целевой точки."""
    if not center_line:
        return current_pos
    for point in center_line:
        if math.hypot(point[0] - current_pos[0], point[1] - current_pos[1]) >= LOOKAHEAD_DISTANCE:
            return point
    return center_line[-1]

def calculate_steering_angle(current_pos, current_heading, target_point):
    """Вычисление угла поворота."""
    dx = target_point[0] - current_pos[0]
    dy = target_point[1] - current_pos[1]
    angle_to_target = math.atan2(dy, dx)
    steering_angle = (angle_to_target - current_heading + math.pi) % (2 * math.pi) - math.pi
    return max(-MAX_TURN_ANGLE, min(MAX_TURN_ANGLE, KP_STEERING * steering_angle))

def adjust_speed(steering_angle, min_distance):
    """Регулировка скорости."""
    speed = BASE_SPEED * (1 - abs(steering_angle) / MAX_TURN_ANGLE * 0.5)  # Уменьшено влияние угла
    if min_distance and min_distance < 2.0:
        speed *= max(0.5, min_distance / 2.0)
    return max(MIN_SPEED, speed)

def draw_path(frame, center_line):
    """Отрисовка траектории."""
    if len(center_line) < 2:
        return frame
    for i in range(1, len(center_line)):
        p1, p2 = center_line[i - 1], center_line[i]
        cv2.line(frame, (int(p1[0]), int(p1[1])), (int(p2[0]), int(p2[1])), (0, 255, 0), 2)
    return frame

def main():
    # Инициализация ZED
    zed = sl.Camera()
    init_params = sl.InitParameters()
    init_params.camera_resolution = sl.RESOLUTION.HD720
    init_params.camera_fps = 30
    init_params.depth_mode = sl.DEPTH_MODE.PERFORMANCE
    init_params.coordinate_units = sl.UNIT.METER

    if zed.open(init_params) != sl.ERROR_CODE.SUCCESS:
        print("Ошибка: не удалось открыть ZED")
        return

    # Получение параметров калибровки
    camera_params = zed.get_camera_information().camera_configuration.calibration_parameters

    # Инициализация Arduino
    car = CarController(arduino_port="/dev/ttyUSB0", baud_rate=9600)
    car.set_gear("turtle")

    image_zed = sl.Mat()
    depth_zed = sl.Mat()
    prev_time = time.time()
    last_valid_path = []

    try:
        while True:
            if zed.grab(sl.RuntimeParameters()) != sl.ERROR_CODE.SUCCESS:
                print("Ошибка: не удалось захватить кадр")
                continue

            zed.retrieve_image(image_zed, sl.VIEW.LEFT)
            zed.retrieve_measure(depth_zed, sl.MEASURE.DEPTH)
            frame = image_zed.get_data()[:, :, :3].copy()
            depth_data = depth_zed.get_data()

            # Обнаружение конусов
            blue_cones, yellow_cones, orange_cones, min_distance = detect_cones(frame, depth_data, camera_params)

            # Остановка при оранжевом конусе
            if any(distance and distance < ORANGE_STOP_DISTANCE for _, _, distance in orange_cones):
                print("Оранжевый конус, остановка")
                car.update(speed=0.0, brake=1.0, steering=0.0)
                time.sleep(1)
                car.stop()
                break

            # Построение траектории
            blue_cones = smooth_path(blue_cones)
            yellow_cones = smooth_path(yellow_cones)
            blue_cones, yellow_cones = balance_cones(blue_cones, yellow_cones)
            center_line = calculate_center_line(blue_cones, yellow_cones)
            if len(center_line) >= 2:  # Минимум 2 точки для траектории
                last_valid_path = center_line

            global CURRENT_HEADING
            # Управление
            target_point = find_target_point(center_line or last_valid_path, CURRENT_POS)
            steering_angle = calculate_steering_angle(CURRENT_POS, CURRENT_HEADING, target_point)
            speed = adjust_speed(steering_angle, min_distance)

            # Обновление направления
            delta_time = time.time() - prev_time
            prev_time = time.time()
            CURRENT_HEADING += (steering_angle / MAX_TURN_ANGLE) * delta_time * 0.5
            CURRENT_HEADING = (CURRENT_HEADING + math.pi) % (2 * math.pi) - math.pi

            # Команды Arduino
            steering = steering_angle / MAX_TURN_ANGLE
            if not center_line and not last_valid_path:
                print("Нет траектории, движение прямо")
                car.update(speed=MIN_SPEED, brake=0.0, steering=0.0)
            else:
                print(f"Скорость: {speed:.2f}, угол: {math.degrees(steering_angle):.1f}°")
                car.update(speed=speed, brake=0.0, steering=steering)

            # Визуализация
            frame = draw_path(frame, center_line or last_valid_path)
            cv2.circle(frame, (int(target_point[0]), int(target_point[1])), 8, (0, 0, 255), -1)
            cv2.circle(frame, (int(CURRENT_POS[0]), int(CURRENT_POS[1])), 10, (255, 255, 255), 2)
            cv2.putText(frame, f"Speed: {speed:.2f}", (30, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(frame, f"Angle: {math.degrees(steering_angle):.1f}°", (30, 80), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.imshow("Trajectory", frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    finally:
        zed.close()
        car.close()
        cv2.destroyAllWindows()
        print("ZED и Arduino отключены")

if __name__ == "__main__":
    main()