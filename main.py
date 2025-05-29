from car_controller.core.communication import MessageBroker
from car_controller.core.config.settings import Settings
from car_controller.processes import CameraProcess, ControlProcess, ArduinoProcess


def main():
    broker = MessageBroker()
    settings = Settings()  # Используем настройки по умолчанию

    processes = [
        CameraProcess(broker, settings),
        ControlProcess(broker, settings),
        ArduinoProcess(broker, settings)
    ]

    for process in processes:
        process.start()

    try:
        for process in processes:
            process.join()
    except KeyboardInterrupt:
        for process in processes:
            process.terminate()


if __name__ == "__main__":
    main()