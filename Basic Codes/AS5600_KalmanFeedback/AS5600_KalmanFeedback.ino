#include <SimpleKalmanFilter.h>

const int encoderPin = A0;

// Parameters: (measurement error, estimate error, process noise)
SimpleKalmanFilter kalman(2, 2, 0.01);

void setup() {
  Serial.begin(115200);
}

int readAverage() {
  long sum = 0;
  for (int i = 0; i < 5; i++) {
    sum += analogRead(encoderPin);
  }
  return sum / 5;
}

void loop() {
  // Read analog (averaged)
  int raw = analogRead(encoderPin);

  // Apply Kalman filter
  float filtered = kalman.updateEstimate(raw);

  // Convert to angle
  float angle = (filtered / 1023.0) * 360.0;

  Serial.print("Raw: ");
  Serial.print(raw);

  Serial.print("  Filtered: ");
  Serial.print(filtered);

  Serial.print("  Angle: ");
  Serial.println(angle);

  delay(10);
}