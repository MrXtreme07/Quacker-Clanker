#define SENSOR_PIN A0

void setup() {
  Serial.begin(115200);
}

void loop() {
  int rawValue = analogRead(SENSOR_PIN);   // 0–1023
  float voltage = rawValue * (5.0 / 1023.0);
  float angle = rawValue * (360.0 / 1023.0);

  Serial.print("Raw: ");
  Serial.print(rawValue);
  Serial.print("  Voltage: ");
  Serial.print(voltage);
  Serial.print(" V  Angle: ");
  Serial.print(angle);
  Serial.println(" deg");

  delay(100);
}