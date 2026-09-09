// POI Arduino serial bridge — examples/arduino_serial.poi 와 함께 사용
// 지원 명령: DWRITE <pin> <0|1>, PWM <pin> <0..255>, AREAD <pin>
String line;

void setup() {
  Serial.begin(115200);
  pinMode(13, OUTPUT);
}

void loop() {
  if (!Serial.available()) return;
  line = Serial.readStringUntil('\n');
  line.trim();

  int first = line.indexOf(' ');
  int second = line.indexOf(' ', first + 1);
  String command = first < 0 ? line : line.substring(0, first);
  int pin = first < 0 ? 0 : line.substring(first + 1, second < 0 ? line.length() : second).toInt();

  if (command == "DWRITE" && second > 0) {
    pinMode(pin, OUTPUT);
    digitalWrite(pin, line.substring(second + 1).toInt() ? HIGH : LOW);
    Serial.println("OK");
  } else if (command == "PWM" && second > 0) {
    pinMode(pin, OUTPUT);
    analogWrite(pin, constrain(line.substring(second + 1).toInt(), 0, 255));
    Serial.println("OK");
  } else if (command == "AREAD") {
    Serial.println(analogRead(pin));
  } else {
    Serial.println("ERROR unknown command");
  }
}
