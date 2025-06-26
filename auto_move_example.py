from ultralytics import YOLO
import pyzed.sl as sl
import cv2
import numpy as np
from car_controller.car_controller import CarController
import time
import math
import os

# Универсальный путь к модели
MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "cone_detector.engine")
if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(f"Модель не найдена: {MODEL_PATH}")
model = YOLO(MODEL_PATH)

# Цвета для визуализации
class_colors = {
    "Yellow": (0, 255, 255),
    "Blue": (255, 0, 0),
    "Orange": (0, 165, 255)
}

# Константы
WINDOW_SIZE = [1280, 720]
CURRENT_POS = (WINDOW_SIZE[0] // 2, WINDOW_SIZE[1] - 50)
CURRENT_HEADING = -math.pi / 2
BASE_SPEED = 0.8  # Базовая скорость (м/с)
MIN_SPEED = 0.5   # Минимальная скорость (м/с)
MAX_SPEED = 1.0   # Максимальная скорость (м/с)
ORANGE_STOP_DISTANCE = 0.4  # Порог остановки для оранжевого конуса (м)
MAX_TURN_ANGLE = math.radians(30)  # Максимальный угол поворота
MIN_ZEROING_ANGLE = math.radians(1)  # Минимальный угол для обнуления
LOOKAHEAD_DISTANCE = 150  # Дистанция до целевой точки (пиксели)
KP_STEERING = 0.8  # Коэффициент пропорциональности для угла поворота
BRAKE_ASPECT = 2.0  # Влияние угла поворота на снижение скорости
FILTER_SIZE = 3    # Размер окна для сглаживания траектории
CONF_THRESHOLD = 0.5  # Порог уверенности для обнаружения конусов
RED_CONES_STOP_THRESHOLD = 1  # Количество оранжевых конусов для остановки

# Хранилище последней траектории
last_valid_path = []

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

def balance_cones(blue_cones, yellow_cones):
    """Балансировка количества синих и желтых конусов."""
    if len(blue_cones) == 0 and len(yellow_cones) > 0:
        blue_cones = [(0, yellow[1]) for yellow in yellow_cones]
    elif len(yellow_cones) == 0 and len(blue_cones) > 0:
        yellow_cones = [(WINDOW_SIZE[0], blue[1]) for blue in blue_cones]
    return blue_cones, yellow_cones

def calculate_center_line(blue_cones, yellow_cones):
    """Вычисление центральной линии между конусами."""
    center_line = []
    min_len = min(len(blue_cones), len(yellow_cones))
    for i in range(min_len):
        center_x = (blue_cones[i][0] + yellow_cones[i][0]) / 2
        center_y = (blue_cones[i][1] + yellow_cones[i][1]) / 2
        center_line.append((center_x, center_y))
    return center_line

def smooth_path(cones, filter_size=FILTER_SIZE):
    """Сглаживание траектории путем усреднения координат."""
    if len(cones) < 2:
        return cones
    smoothed_cones = []
    for i in range(len(cones)):
        start = max(0, i - filter_size // 2)
        end = min(len(cones), i + filter_size // 2 + 1)
        avg_x = np.mean([cone[0] for cone in cones[start:end]])
        avg_y = np.mean([cone[1] for cone in cones[start:end]])
        smoothed_cones.append((int(avg_x), int(avg_y)))
    return smoothed_cones

def find_target_point(center_line, current_position):
    """Поиск целевой точки на расстоянии LOOKAHEAD_DISTANCE."""
    if not center_line:
        return current_position
    for point in center_line:
        distance = math.sqrt((point[0] - current_position[0])**2 + (point[1] - current_position[1])**2)
        if distance >= LOOKAHEAD_DISTANCE:
            return point
    return center_line[-1] if center_line else current_position

def calculate_steering_angle(current_position, current_heading, target_point):
    """Вычисление угла поворота для достижения целевой точки."""
    dx = target_point[0] - current_position[0]
    dy = target_point[1] - current_position[1]
    angle_to_target = math.atan2(dy, dx)
    steering_angle = angle_to_target - current_heading
    steering_angle = (steering_angle + math.pi) % (2 * math.pi) - math.pi
    final_angle = max(-MAX_TURN_ANGLE, min(MAX_TURN_ANGLE, KP_STEERING * steering_angle))
    if abs(final_angle) < MIN_ZEROING_ANGLE:
        final_angle = 0
    return final_angle

def adjust_speed(steering_angle, min_distance):
    """Регулировка скорости в зависимости от угла поворота и расстояния."""
    speed = BASE_SPEED * (1 - (abs(steering_angle) / MAX_TURN_ANGLE)**BRAKE_ASPECT)
    if min_distance is not None and min_distance < 2.0:
        speed *= max(0.5, min_distance / 2.0)
    return max(MIN_SPEED, min(MAX_SPEED, speed))

def interpolate_color(distance, max_distance=150):
    """Интерполяция цвета для визуализации траектории."""
    normalized_distance = min(distance / max_distance, 1)
    red = int(255 * normalized_distance)
    green = int(255 * (1 - normalized_distance))
    return (0, green, red)

def draw_colored_path(frame, center_line):
    """Отрисовка траектории с цветом, зависящим от расстояния."""
    if len(center_line) < 2:
        return frame
    for i in range(1, len(center_line)):
        p1 = center_line[i - 1]
        p2 = center_line[i]
        distance = math.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
        color = interpolate_color(distance)
        cv2.line(frame, (int(p1[0]), int(p1[1])), (int(p2[0]), int(p2[1])), color, 2)
    return frame

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

    # Инициализация Arduino
    arduino_port = "/dev/ttyUSB0"
    baud_rate = 9600
    car = CarController(arduino_port=arduino_port, baud_rate=baud_rate)
    car.set_gear("turtle")

    image_zed = sl.Mat()
    depth_zed = sl.Mat()
    prev_time = time.time()

    global CURRENT_HEADING, last_valid_path
    try:
        while True:
            if zed.grab(sl.RuntimeParameters()) == sl.ERROR_CODE.SUCCESS:
                zed.retrieve_image(image_zed, sl.VIEW.LEFT)
                zed.retrieve_measure(depth_zed, sl.MEASURE.DEPTH)
                frame = image_zed.get_data()[:, :, :3].copy()
                depth_data = depth_zed.get_data()

                # Обнаружение конусов
                results = model(frame)
                blue_cones = []
                yellow_cones = []
                orange_cones = []
                min_distance = float('inf')

                for result in results:
                    boxes = result.boxes
                    for box in boxes:
                        conf = float(box.conf[0])
                        if conf < CONF_THRESHOLD:
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
                            blue_cones.append((cx, cy))
                        elif label == "Yellow":
                            yellow_cones.append((cx, cy))
                        elif label == "Orange":
                            orange_cones.append((cx, cy, distance))

                # Проверка на остановку
                if any(distance is not None and distance < ORANGE_STOP_DISTANCE for _, _, distance in orange_cones):
                    print("Обнаружен оранжевый конус, остановка")
                    car.update(speed=0.0, brake=1.0, steering=0.0)
                    time.sleep(1)
                    car.stop()
                    break

                # Сглаживание и балансировка конусов
                blue_cones = smooth_path(blue_cones)
                yellow_cones = smooth_path(yellow_cones)
                blue_cones, yellow_cones = balance_cones(blue_cones, yellow_cones)

                # Построение центральной линии
                center_line = calculate_center_line(blue_cones, yellow_cones)
                if center_line:
                    last_valid_path = center_line

                # Поиск целевой точки
                target_point = find_target_point(center_line if center_line else last_valid_path, CURRENT_POS)

                # Вычисление угла поворота
                steering_angle = calculate_steering_angle(CURRENT_POS, CURRENT_HEADING, target_point)

                # Регулировка скорости
                speed = adjust_speed(steering_angle, min_distance)

                # Обновление направления
                current_time = time.time()
                delta_time = current_time - prev_time
                prev_time = current_time
                CURRENT_HEADING += (steering_angle / MAX_TURN_ANGLE) * delta_time * 0.5
                CURRENT_HEADING = (CURRENT_HEADING + math.pi) % (2 * math.pi) - math.pi

                # Визуализация
                draw_colored_path(frame, center_line if center_line else last_valid_path)
                cv2.circle(frame, (int(target_point[0]), int(target_point[1])), 8, (0, 0, 255), -1)
                cv2.circle(frame, (int(CURRENT_POS[0]), int(CURRENT_POS[1])), 10, (255, 255, 255), 2)

                # Вывод информации на кадр
                text_speed = f"Speed: {speed:.2f} m/s"
                text_steering = f"Angle: {math.degrees(steering_angle):.1f}°"
                cv2.putText(frame, text_speed, (30, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
                cv2.putText(frame, text_steering, (30, 80), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)

                # Отправка команд на Arduino
                if not center_line and not last_valid_path:
                    print("Недостаточно точек и нет сохраненной траектории, движение прямо")
                    car.update(speed=MIN_SPEED, brake=0.0, steering=0.0)
                    arduino_cmd_text = f"CMD: motor={car.motor_value}, steering={car.steering}"
                else:
                    steering = steering_angle / MAX_TURN_ANGLE
                    steering = max(min(steering, 1.0), -1.0)
                    print(f"Управление: скорость={speed:.2f}, угол={steering:.2f}, расстояние={min_distance:.2f}m")
                    car.update(speed=speed, brake=0.0, steering=steering)
                    arduino_cmd_text = f"CMD: motor={car.motor_value}, steering={car.steering}"

                cv2.putText(frame, arduino_cmd_text, (30, 120), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)

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