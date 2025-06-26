from ultralytics import YOLO
import pyzed.sl as sl
import cv2
import numpy as np
from car_controller.car_controller import CarController
import time
import math
from scipy.interpolate import splprep, splev
import os

# Универсальный путь к модели
MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "cone_detector.engine")
if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(f"Модель не найдена: {MODEL_PATH}")
model = YOLO(MODEL_PATH)

class_colors = {
    "Yellow": (0, 255, 255),
    "Blue": (255, 0, 0),
    "Orange": (0, 165, 255)
}

WINDOW_SIZE = [1280, 720]
CURRENT_POS = (WINDOW_SIZE[0] // 2, WINDOW_SIZE[1] - 50)
CURRENT_HEADING = -math.pi / 2
BASE_SPEED = 1.0
MIN_SPEED = 0.8
MAX_SPEED = 1.2
ORANGE_STOP_DISTANCE = 0.4
SMOOTH_FACTOR = 1.5
MAX_TURN_ANGLE = math.radians(30)
MIN_ZEROING_ANGLE = math.radians(1)
MIN_PATH_POINTS = 3
OFFSET_DISTANCE = 200
LOOKAHEAD_BASE = 150
K_CURVATURE = 0.5
CONF_THRESHOLD = 0.5
MAX_DISTANCE = 5.0  # Максимальное расстояние для учета конусов
ORANGE_CONFIRM_FRAMES = 3  # Количество кадров для подтверждения оранжевого конуса

last_valid_path = []
orange_cone_count = 0  # Счетчик кадров для подтверждения оранжевого конуса


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


def filter_cones(cones):
    """Фильтрация конусов по расстоянию и координатам."""
    filtered = []
    for cone in cones:
        x, y, distance = cone
        if distance is not None and distance < MAX_DISTANCE:
            if 0 <= x <= WINDOW_SIZE[0] and 0 <= y <= WINDOW_SIZE[1]:
                filtered.append(cone)
    return filtered


def build_cone_path(cones):
    if len(cones) < 2:
        return [(c[0], c[1]) for c in cones] if cones else []
    cones = sorted(cones, key=lambda x: x[2] if x[2] is not None else float('inf'))
    path = [(c[0], c[1]) for c in cones]
    x, y = zip(*path)
    try:
        tck, u = splprep([x, y], s=SMOOTH_FACTOR, k=min(3, len(path) - 1))
        u_fine = np.linspace(0, 1, max(10, len(path) * 2))
        x_fine, y_fine = splev(u_fine, tck)
        return [(x, y) for x, y in zip(x_fine, y_fine) if 0 <= x <= WINDOW_SIZE[0] and 0 <= y <= WINDOW_SIZE[1]]
    except:
        return path


def calculate_trajectory(blue_cones, yellow_cones, min_distance):
    global last_valid_path
    blue_cones = filter_cones(blue_cones)
    yellow_cones = filter_cones(yellow_cones)
    
    blue_path = build_cone_path(blue_cones)
    yellow_path = build_cone_path(yellow_cones)

    if not blue_path and yellow_path:
        offset = OFFSET_DISTANCE * max(0.5, min(1.0, min_distance / 2.0))
        center_line = [(max(0, p[0] - offset), p[1]) for p in yellow_path]
    elif not yellow_path and blue_path:
        offset = OFFSET_DISTANCE * max(0.5, min(1.0, min_distance / 2.0))
        center_line = [(min(WINDOW_SIZE[0], p[0] + offset), p[1]) for p in blue_path]
    elif not blue_path and not yellow_path:
        return last_valid_path
    else:
        center_line = []
        min_len = min(len(blue_path), len(yellow_path))
        for i in range(min_len):
            center_x = (blue_path[i][0] + yellow_path[i][0]) / 2
            center_y = (blue_path[i][1] + yellow_path[i][1]) / 2
            center_line.append((center_x, center_y))
        if len(blue_path) > min_len:
            for i in range(min_len, len(blue_path)):
                center_x = (blue_path[i][0] + WINDOW_SIZE[0]) / 2
                center_y = blue_path[i][1]
                center_line.append((center_x, center_y))
        elif len(yellow_path) > min_len:
            for i in range(min_len, len(yellow_path)):
                center_x = (0 + yellow_path[i][0]) / 2
                center_y = yellow_path[i][1]
                center_line.append((center_x, center_y))

    center_line = [(x, y) for x, y in center_line if 0 <= x <= WINDOW_SIZE[0] and 0 <= y <= WINDOW_SIZE[1]]
    if len(center_line) >= MIN_PATH_POINTS:
        last_valid_path = center_line
    return center_line


def stanley_controller(current_pos, current_heading, path, speed, min_distance, k_stanley=0.5, epsilon=1e-3):
    if not path or len(path) < MIN_PATH_POINTS:
        return 0.0, current_pos

    # Адаптивный lookahead
    lookahead = LOOKAHEAD_BASE * max(0.5, min(1.0, min_distance / 2.0))
    
    # Найти ближайшую точку на траектории
    dists = [math.hypot(p[0] - current_pos[0], p[1] - current_pos[1]) for p in path]
    min_idx = int(np.argmin(dists))
    
    # Найти точку lookahead
    target_idx = min_idx
    for i in range(min_idx, len(path)):
        if math.hypot(path[i][0] - current_pos[0], path[i][1] - current_pos[1]) > lookahead:
            target_idx = i
            break
    target_point = path[target_idx]

    # Вектор направления траектории
    if target_idx < len(path) - 1:
        next_point = path[target_idx + 1]
    else:
        next_point = path[target_idx]
    path_dx = next_point[0] - target_point[0]
    path_dy = next_point[1] - target_point[1]
    path_yaw = math.atan2(path_dy, path_dx)

    # Heading error
    heading_error = (path_yaw - current_heading + math.pi) % (2 * math.pi) - math.pi

    # Cross-track error
    dx = target_point[0] - current_pos[0]
    dy = target_point[1] - current_pos[1]
    cross_track_error = math.sin(path_yaw) * dx - math.cos(path_yaw) * dy

    # Адаптивный коэффициент k_stanley
    k_stanley_adapted = k_stanley * max(0.5, min(1.0, min_distance / 2.0))
    
    # Stanley control law
    steering_angle = heading_error + math.atan2(k_stanley_adapted * cross_track_error, speed + epsilon)
    steering_angle = max(-MAX_TURN_ANGLE, min(MAX_TURN_ANGLE, steering_angle))
    if abs(steering_angle) < MIN_ZEROING_ANGLE:
        steering_angle = 0
    print(f"Stanley: heading_error={heading_error:.2f}, cross_track_error={cross_track_error:.2f}, steering={steering_angle:.2f}")
    return steering_angle, target_point


def estimate_curvature(path):
    if len(path) < 3:
        return 0.0
    p1, p2, p3 = path[:3]
    v1 = np.array([p2[0] - p1[0], p2[1] - p1[1]])
    v2 = np.array([p3[0] - p2[0], p3[1] - p2[1]])
    norm_v1 = np.linalg.norm(v1)
    norm_v2 = np.linalg.norm(v2)
    if norm_v1 == 0 or norm_v2 == 0:
        return 0.0
    angle = math.acos(np.clip(np.dot(v1, v2) / (norm_v1 * norm_v2), -1, 1))
    return angle / math.radians(180)


def adjust_speed(steering_angle, curvature, min_distance):
    norm_speed = BASE_SPEED * (1 - 0.6 * curvature - 0.3 * (abs(steering_angle) / MAX_TURN_ANGLE))
    if min_distance is not None and min_distance < 2.0:
        norm_speed *= max(0.4, min_distance / 2.0)
    norm_speed = max(0.0, min(1.0, norm_speed))
    scaled_speed = MIN_SPEED + (MAX_SPEED - MIN_SPEED) * norm_speed
    return scaled_speed


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
    arduino_port = "/dev/ttyUSB0"
    baud_rate = 9600
    car = CarController(arduino_port=arduino_port, baud_rate=baud_rate)
    car.set_gear("turtle")

    image_zed = sl.Mat()
    depth_zed = sl.Mat()
    prev_time = time.time()

    global CURRENT_HEADING, last_valid_path, orange_cone_count
    try:
        while True:
            if zed.grab(sl.RuntimeParameters()) == sl.ERROR_CODE.SUCCESS:
                zed.retrieve_image(image_zed, sl.VIEW.LEFT)
                zed.retrieve_measure(depth_zed, sl.MEASURE.DEPTH)
                frame = image_zed.get_data()[:, :, :3].copy()
                depth_data = depth_zed.get_data()

                results = model(frame)
                blue_cones = []
                yellow_cones = []
                stop = False
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
                            blue_cones.append((cx, cy, distance))
                        elif label == "Yellow":
                            yellow_cones.append((cx, cy, distance))
                        elif label == "Orange" and distance is not None and distance < ORANGE_STOP_DISTANCE:
                            orange_cone_count += 1
                            if orange_cone_count >= ORANGE_CONFIRM_FRAMES:
                                stop = True
                        else:
                            orange_cone_count = max(0, orange_cone_count - 1)

                if stop:
                    print("Обнаружен оранжевый конус, остановка")
                    car.update(speed=0.0, brake=1.0, steering=0.0)
                    time.sleep(1)
                    car.stop()
                    break

                center_line = calculate_trajectory(blue_cones, yellow_cones, min_distance)
                speed = adjust_speed(0, 0, min_distance)
                steering_angle, target_point = stanley_controller(CURRENT_POS, CURRENT_HEADING, center_line, speed, min_distance)
                curvature = estimate_curvature(center_line)
                speed = adjust_speed(steering_angle, curvature, min_distance)

                current_time = time.time()
                delta_time = current_time - prev_time
                prev_time = current_time
                CURRENT_HEADING += (steering_angle / MAX_TURN_ANGLE) * delta_time * 0.5
                CURRENT_HEADING = (CURRENT_HEADING + math.pi) % (2 * math.pi) - math.pi

                if center_line:
                    draw_colored_path(frame, center_line)
                cv2.circle(frame, (int(target_point[0]), int(target_point[1])), 8, (0, 0, 255), -1)
                cv2.circle(frame, (int(CURRENT_POS[0]), int(CURRENT_POS[1])), 10, (255, 255, 255), 2)

                text_speed = f"Speed: {speed:.2f} m/s"
                text_steering = f"Angle: {steering_angle * 180 / 3.1415:.1f}o"
                cv2.putText(frame, text_speed, (30, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
                cv2.putText(frame, text_steering, (30, 80), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)

                if len(center_line) < MIN_PATH_POINTS and not last_valid_path:
                    print("Недостаточно точек и нет сохраненной траектории, движение прямо")
                    car.update(speed=BASE_SPEED * 0.5, brake=0.0, steering=0.0)
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