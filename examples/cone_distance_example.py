"""Пример детекции конусов моделью YOLO с использованием карты
глубины ZED-камеры для оценки расстояния до каждого конуса."""

from ultralytics import YOLO
import pyzed.sl as sl
import cv2
import numpy as np


model = YOLO("models/cone_detector.pt")

class_colors = {
    "Yellow": (0, 255, 255),
    "Blue": (255, 0, 0),
    "Orange": (0, 165, 255)
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

    image_zed = sl.Mat()
    depth_zed = sl.Mat()

    try:
        while True:
            if zed.grab(sl.RuntimeParameters()) == sl.ERROR_CODE.SUCCESS:
                zed.retrieve_image(image_zed, sl.VIEW.LEFT)
                zed.retrieve_measure(depth_zed, sl.MEASURE.DEPTH)
                frame = image_zed.get_data()[:, :, :3].copy()
                depth_data = depth_zed.get_data()

                results = model(frame)
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
                        # Определяем расстояние
                        distance = get_box_distance(depth_data, x1, y1, x2, y2)
                        # Рисуем бокс
                        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                        label_text = f"{label} {conf:.2f}"
                        if distance is not None:
                            label_text += f" {distance:.2f}m"
                        else:
                            label_text += " ?m"
                        cv2.putText(frame, label_text, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

                cv2.imshow("YOLOv8 + Distance (ZED)", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
            else:
                print("Ошибка: не удалось захватить кадр")
    finally:
        zed.close()
        cv2.destroyAllWindows()
        print("ZED-камера отключена")

if __name__ == "__main__":
    main()
