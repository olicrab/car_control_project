"""Пример использования модели YOLO с ZED-камерой для детекции дорожных
конусов без управления автомобилем."""

from ultralytics import YOLO
import pyzed.sl as sl
import cv2
import numpy as np


model = YOLO("models/cone_detector.pt")

# Определение цветов для классов (BGR формат для OpenCV)
class_colors = {
    "Yellow": (0, 255, 255),  # Желтый
    "Blue": (255, 0, 0),      # Синий
    "Orange": (0, 165, 255)   # Оранжевый
}

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

    try:
        while True:
            if zed.grab(sl.RuntimeParameters()) == sl.ERROR_CODE.SUCCESS:
                zed.retrieve_image(image_zed, sl.VIEW.LEFT)
                frame = image_zed.get_data()[:, :, :3].copy()

                # YOLO детекция
                results = model(frame)

                for result in results:
                    boxes = result.boxes
                    for box in boxes:
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        conf = box.conf[0]
                        cls = int(box.cls[0])
                        label = model.names[cls]
                        color = class_colors.get(label, (0, 255, 0))
                        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                        label_text = f"{label} {conf:.2f}"
                        cv2.putText(frame, label_text, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

                cv2.imshow("YOLOv8 Detection (ZED)", frame)

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
