from ultralytics import YOLO
import pyzed.sl as sl
import cv2
import numpy as np
from car_controller.car_controller import CarController
import time
import math
from scipy.interpolate import splprep, splev

model = YOLO("models/cone_detector.pt")

class_colors = {
    "Yellow": (0, 255, 255),
    "Blue": (255, 0, 0),
    "Orange": (0, 165, 255)
}

WINDOW_SIZE = [1280, 720]
CURRENT_POS = (WINDOW_SIZE[0] // 2, WINDOW_SIZE[1] - 50)
CURRENT_HEADING = -math.pi / 2
K_CROSS = 0.5  # Уменьшено для стабильности
K_HEADING = 0.5  # Увеличено для большей реакции
BASE_SPEED = 0.5
MIN_SPEED = 0.1
ORANGE_STOP_DISTANCE = 1.0
SMOOTH_FACTOR = 2.0
MAX_TURN_ANGLE = math.radians(30)
MIN_ZEROING_ANGLE = math.radians(1)  # Еще меньше для чувствительности


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


def build_cone_path(cones):
    cones = sorted(cones, key=lambda x: x[2] if x[2] is not None else float('inf'))
    if not cones:
        return []
    path = [(c[0], c[1]) for c in cones]
    if len(path) < 2:
        return path
    x, y = zip(*path)
    try:
        tck, u = splprep([x, y], s=SMOOTH_FACTOR, k=min(3, len(path) - 1))
        u_fine = np.linspace(0, 1, max(10, len(path) * 2))
        x_fine, y_fine = splev(u_fine, tck)
        return list(zip(x_fine, y_fine))
    except:
        return path


def calculate_trajectory(blue_cones, yellow_cones):
    blue_path = build_cone_path(blue_cones)
    yellow_path = build_cone_path(yellow_cones)
    if not blue_path and yellow_path:
        blue_path = [(0, y) for _, y in yellow_path]
    elif not yellow_path and blue_path:
        yellow_path = [(WINDOW_SIZE[0], y) for _, y in blue_path]
    elif not blue_path and not yellow_path:
        return []
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
    # Проверка валидности точек
    center_line = [(x, y) for x, y in center_line if 0 <= x <= WINDOW_SIZE[0] and 0 <= y <= WINDOW_SIZE[1]]
    return center_line


def stanley_controller(current_pos, current_heading, path):
    if not path or len(path) < 2:
        return 0.0, current_pos
    # Находим ближайшую точку
    distances = [math.sqrt((p[0] - current_pos[0]) ** 2 + (p[1] - current_pos[1]) ** 2) for p in path]
    closest_idx = np.argmin(distances)
    closest_point = path[closest_idx]

    # Нормализуем поперечную ошибку (в пикселях, делим на ширину кадра)
    cross_error = distances[closest_idx] / (WINDOW_SIZE[0] / 2)

    # Вычисляем направление траектории
    path_heading = current_heading
    if closest_idx < len(path) - 1:
        dx = path[closest_idx + 1][0] - closest_point[0]
        dy = path[closest_idx + 1][1] - closest_point[1]
        if dx != 0 or dy != 0:
            path_heading = math.atan2(dy, dx)
    heading_error = (path_heading - current_heading + math.pi) % (2 * math.pi) - math.pi

    # Угол руления
    steering_angle = K_HEADING * heading_error + K_CROSS * math.atan2(cross_error, 1.0)
    steering_angle = max(-MAX_TURN_ANGLE, min(MAX_TURN_ANGLE, steering_angle))
    if abs(steering_angle) < MIN_ZEROING_ANGLE:
        steering_angle = 0

    print(f"cross_error={cross_error:.2f}, heading_error={heading_error:.2f}, path_heading={path_heading:.2f}")
    return steering_angle, closest_point


def estimate_curvature(path):
    if len(path) < 3:
        return 0.0
    p1, p2, p3 = path[:3]
    v1 = np.array([p2[0] - p1[0], p2[1] - p1[1]])
    v2 = np.array([p3[0] - p2[0], p3[1] - p2[1]])
    angle = math.acos(np.clip(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)), -1, 1))
    return angle / math.radians(180)


def adjust_speed(steering_angle, curvature, min_distance):
    speed = BASE_SPEED * (1 - 0.7 * curvature - 0.3 * (abs(steering_angle) / MAX_TURN_ANGLE))
    if min_distance is not None and min_distance < 2.0:
        speed *= max(0.5, min_distance / 2.0)
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
    prev_time = time.time()

    global CURRENT_HEADING
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

                center_line = calculate_trajectory(blue_cones, yellow_cones)
                steering_angle, target_point = stanley_controller(CURRENT_POS, CURRENT_HEADING, center_line)
                curvature = estimate_curvature(center_line)
                speed = adjust_speed(steering_angle, curvature, min_distance)

                # Обновляем CURRENT_HEADING
                current_time = time.time()
                delta_time = current_time - prev_time
                prev_time = current_time
                CURRENT_HEADING += (steering_angle / MAX_TURN_ANGLE) * delta_time * 0.5  # Уменьшено для стабильности
                CURRENT_HEADING = (CURRENT_HEADING + math.pi) % (2 * math.pi) - math.pi

                if center_line:
                    draw_colored_path(frame, center_line)
                cv2.circle(frame, (int(target_point[0]), int(target_point[1])), 8, (0, 0, 255), -1)
                cv2.circle(frame, (int(CURRENT_POS[0]), int(CURRENT_POS[1])), 10, (255, 255, 255), 2)

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