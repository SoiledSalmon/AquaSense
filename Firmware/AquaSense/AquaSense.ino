#include <WiFi.h>
#include <ThingSpeak.h>

// -------------------------
// WiFi Credentials
// -------------------------
const char* ssid = "Ananth's Oppo A17";
const char* password = "Anipollu123";

// -------------------------
// ThingSpeak Details
// -------------------------
unsigned long channelID = 3406577;
const char * writeAPIKey = "KWT3638R6HM9UYXQ";

WiFiClient client;

// -------------------------
// Sensor Pins (ESP32 ADC1 channels - safe to use alongside WiFi)
// -------------------------
const int phSensorPin = 34;
const int turbidityPin = 36;
const int tdsPin = 32;

// -------------------------
// Turbidity sensor: HARDWARE FIX REQUIRED
// -------------------------
// This turbidity sensor outputs 0-4.5V (clear water reads ~4.1-4.2V at 5V supply).
// The ESP32 ADC is only rated for 0-3.3V. Wired directly, the pin reads its
// maximum code (clipped) for any input above ~3.3V - which covers clear water
// AND mildly turbid water. This is almost certainly why your readings "don't
// change at all": you've only been seeing the clipped ceiling.
//
// Fix: add a voltage divider between the sensor's OUT pin and GPIO36:
//
//   Sensor OUT ---[R1 = 10k]---+---[R2 = 20k]--- GND
//                               |
//                           ESP32 GPIO36
//
// This scales the sensor's 0-4.5V down to a safe 0-3.0V at the ADC pin.
// The code below multiplies the measured voltage back up by the same ratio
// to recover the sensor's true output voltage before applying the NTU formula.
// If you use different resistors, just update the two values below.
const float DIVIDER_R1 = 10000.0; // ohms, sensor OUT -> ADC node
const float DIVIDER_R2 = 20000.0; // ohms, ADC node -> GND
const float TURBIDITY_DIVIDER_RATIO = DIVIDER_R2 / (DIVIDER_R1 + DIVIDER_R2); // ~0.667

// TDS sensor outputs only 0-2.3V max, which already fits safely inside the
// ESP32's 0-3.3V ADC range, so no divider is needed for it.

// -------------------------
// Utility Functions
// -------------------------

int getAverageReading(int analogPin, int samples = 10)
{
  long sum = 0;

  for (int i = 0; i < samples; i++)
  {
    sum += analogRead(analogPin);
    delay(10);
  }

  return sum / samples;
}

// Averages analogReadMilliVolts() instead of raw analogRead() counts.
// The ESP32 ADC is known to be non-linear (especially near 0V and 3.3V), so
// analogReadMilliVolts() (which applies the chip's factory eFuse calibration)
// gives a noticeably more accurate voltage than raw*(3.3/4095.0) would.
float getAverageMilliVolts(int analogPin, int samples = 20)
{
  long sum = 0;

  for (int i = 0; i < samples; i++)
  {
    sum += analogReadMilliVolts(analogPin);
    delay(10);
  }

  return sum / (float)samples;
}

// Convert voltage to pH (Calibration Required)
float voltageTopH(float voltage)
{
  float m = -1.095;
  float b = 9.7375;

  return (m * voltage + b);
}

// Convert the turbidity sensor's TRUE output voltage (after undoing the
// divider) into NTU (Nephelometric Turbidity Units).
// Calibration curve from DFRobot's analog turbidity sensor wiki, valid when
// clear water reads ~4.1-4.2V at 5V supply:
//   https://wiki.dfrobot.com/Turbidity_sensor_SKU__SEN0189
// The curve is a downward parabola, only meaningful between ~2.5V-4.2V
// (which covers the sensor's full 0-1000 NTU spec range and a bit beyond).
// Outside that window the polynomial folds back on itself, so it's clamped.
float voltageToNTU(float voltage)
{
  if (voltage >= 4.2) {
    return 0.0;     // at/above the clear-water reference voltage -> 0 NTU
  }
  if (voltage < 2.5) {
    return 3000.0;  // below the curve's valid range -> very high/off-scale turbidity
  }

  float ntu = -1120.4 * voltage * voltage + 5742.3 * voltage - 4352.9;
  return (ntu < 0) ? 0.0 : ntu;
}

// Convert the TDS sensor's output voltage into TDS in ppm, with temperature
// compensation. Calibration curve from DFRobot's Gravity Analog TDS Sensor
// (SEN0244) wiki - this matches the datasheet you provided exactly
// (3.3-5.5V in, 0-2.3V out, 0-1000ppm range, +-10% F.S. accuracy):
//   https://wiki.dfrobot.com/sen0244/docs/20305
float voltageToTDS(float voltage, float temperatureC = 25.0)
{
  float compensationCoefficient = 1.0 + 0.02 * (temperatureC - 25.0);
  float compensationVoltage = voltage / compensationCoefficient;

  float tds = (133.42 * compensationVoltage * compensationVoltage * compensationVoltage
             - 255.86 * compensationVoltage * compensationVoltage
             + 857.39 * compensationVoltage) * 0.5;

  if (tds < 0) tds = 0;
  if (tds > 1000) tds = 1000; // sensor's spec'd measurement ceiling
  return tds;
}

// -------------------------
// Setup
// -------------------------
void setup() {

  Serial.begin(115200);
  delay(3000);   // Give Serial Monitor time to connect

  // Explicit ADC config for reliable, repeatable readings
  analogReadResolution(12);        // 0-4095
  analogSetAttenuation(ADC_11db);  // full ~0-3.3V input range on all ADC1 pins

  Serial.println();
  Serial.println("==============================");
  Serial.println("ESP32 Booted");
  Serial.println("==============================");

  Serial.print("Connecting to: ");
  Serial.println(ssid);

  WiFi.mode(WIFI_STA);
  WiFi.disconnect(true);
  delay(1000);

  WiFi.begin(ssid, password);

  int attempts = 0;

  while (WiFi.status() != WL_CONNECTED && attempts < 30)
  {
    Serial.print(".");

    delay(1000);

    attempts++;

    Serial.print(" Status = ");
    Serial.println(WiFi.status());
  }

  if (WiFi.status() == WL_CONNECTED)
  {
    Serial.println();
    Serial.println("WiFi Connected!");
    Serial.print("IP Address: ");
    Serial.println(WiFi.localIP());

    ThingSpeak.begin(client);
  }
  else
  {
    Serial.println();
    Serial.println("WiFi FAILED!");
  }
}

// -------------------------
// Loop
// -------------------------
void loop()
{
  // ---- pH (unchanged - already confirmed working) ----
  int phRaw = getAverageReading(phSensorPin);
  float phVoltage = phRaw * (3.3 / 4095.0);
  float pH = voltageTopH(phVoltage);

  // ---- Turbidity ----
  float turbidityMeasuredVoltage = getAverageMilliVolts(turbidityPin) / 1000.0; // volts at the ESP32 pin
  float turbiditySensorVoltage = turbidityMeasuredVoltage / TURBIDITY_DIVIDER_RATIO; // recovered sensor output (0-4.5V)
  float turbidityNTU = voltageToNTU(turbiditySensorVoltage);

  // ---- TDS ----
  float tdsVoltage = getAverageMilliVolts(tdsPin) / 1000.0; // 0-2.3V, fits directly in ESP32's 0-3.3V range
  float tdsValue = voltageToTDS(tdsVoltage);

  // Display
  Serial.println("------------------------");
  Serial.print("pH: ");
  Serial.println(pH);

  Serial.print("Turbidity sensor voltage: ");
  Serial.print(turbiditySensorVoltage, 3);
  Serial.println(" V");
  Serial.print("Turbidity: ");
  Serial.print(turbidityNTU, 1);
  Serial.println(" NTU");

  Serial.print("TDS voltage: ");
  Serial.print(tdsVoltage, 3);
  Serial.println(" V");
  Serial.print("TDS: ");
  Serial.print(tdsValue, 1);
  Serial.println(" ppm");

  // Send to ThingSpeak
  ThingSpeak.setField(1, pH);
  ThingSpeak.setField(2, turbidityNTU);
  ThingSpeak.setField(3, tdsValue);

  int response = ThingSpeak.writeFields(channelID, writeAPIKey);

  if (response == 200)
  {
    Serial.println("ThingSpeak Update Successful");
  }
  else
  {
    Serial.print("ThingSpeak Error: ");
    Serial.println(response);
  }

  // ThingSpeak free accounts require at least 15 seconds
  delay(20000);
}
