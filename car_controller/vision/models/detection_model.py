import numpy as np
from typing import List, Tuple
import cv2


class DetectionModel:
    def __init__(self, confidence_threshold: float = 0.5):
        self.confidence_threshold = confidence_threshold
        self.classes = []
        self.net = None

    def initialize(self, model_path: str, config_path: str, classes_path: str) -> None:
        self.net = cv2.dnn.readNet(model_path, config_path)
        with open(classes_path, 'r') as f:
            self.classes = [line.strip() for line in f.readlines()]

    def detect(self, image: np.ndarray) -> List[Tuple[str, float, Tuple[int, int, int, int]]]:
        blob = cv2.dnn.blobFromImage(image, 1 / 255.0, (416, 416), swapRB=True, crop=False)
        self.net.setInput(blob)

        layer_names = self.net.getLayerNames()
        output_layers = [layer_names[i - 1] for i in self.net.getUnconnectedOutLayers()]
        outputs = self.net.forward(output_layers)

        results = []
        for output in outputs:
            for detection in output:
                scores = detection[5:]
                class_id = np.argmax(scores)
                confidence = scores[class_id]

                if confidence > self.confidence_threshold:
                    center_x = int(detection[0] * image.shape[1])
                    center_y = int(detection[1] * image.shape[0])
                    width = int(detection[2] * image.shape[1])
                    height = int(detection[3] * image.shape[0])

                    x = int(center_x - width / 2)
                    y = int(center_y - height / 2)

                    results.append((
                        self.classes[class_id],
                        float(confidence),
                        (x, y, width, height)
                    ))

        return results