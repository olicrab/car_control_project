#include <Servo.h>

int motorPin = 9;        // Пин для ESC (SC-15WP)
int servoPin = 10;       // Пин для сервопривода HPI SF-10W
Servo motorESC;
Servo steeringServo;

void setup() {
  Serial.begin(9600);    // Настройка последовательного порта
  motorESC.attach(motorPin);  // Подключаем ESC
  steeringServo.attach(servoPin);  // Подключаем серво

  motorESC.write(90);  // Мотор остановлен
  steeringServo.write(90);  // Серво в центре
}

void loop() {
  if (Serial.available() > 0) {
    String data = Serial.readStringUntil('\n');  // Чтение всей строки до символа новой строки
    int motorValue = 90;
    int steeringValue = 90;

    // Разделяем строку на два значения
    int commaIndex = data.indexOf(',');  // Ищем запятую
    if (commaIndex != -1) {
      motorValue = data.substring(0, commaIndex).toInt();  // Чтение значения для мотора
      steeringValue = data.substring(commaIndex + 1).toInt();  // Чтение значения для серво
    }

    // Ограничиваем значение для мотора и серво в пределах от 0 до 180
    motorValue = constrain(motorValue, 0, 180);
    steeringValue = constrain(steeringValue, 0, 180);

    motorESC.write(motorValue);  // Устанавливаем значение для мотора
    steeringServo.write(steeringValue);  // Устанавливаем значение для серво
  }
}
