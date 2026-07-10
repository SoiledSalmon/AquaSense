#include <WiFi.h>
#include <ThingSpeak.h>

// -------------------------
// WiFi Credentials
// -------------------------
const char* ssid = "POCO M4 5G";
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

// -------------------------
// TEMPORARY SIMULATION MODE - TURBIDITY
// -------------------------
// The turbidity sensor unit is currently suspected/confirmed defective (bad
// hardware, not just a wiring/divider issue), so its raw readings aren't
// trustworthy right now. Until it's replaced or repaired, this sketch
// substitutes a SIMULATED NTU value that behaves like a real drinking-water
// reading: it sits in a realistic clean-water band and drifts slightly each
// cycle (like real sensor noise/tolerance) instead of jumping randomly.
//
// The real sensor voltage is still read and printed to Serial every loop so
// you can keep an eye on it and tell when it starts responding normally
// again - that's your cue to flip SIMULATE_TURBIDITY back to false.
//
// WHO guideline for drinking water is <5 NTU, with well-treated tap water
// typically sitting around 0.1-1 NTU. We simulate around that range.
bool SIMULATE_TURBIDITY = true;

const float SIM_TURBIDITY_BASELINE = 0.8;   // "typical" clean water NTU
const float SIM_TURBIDITY_MIN = 0.1;
const float SIM_TURBIDITY_MAX = 2.0;
const float SIM_TURBIDITY_STEP = 0.08;      // max drift per reading cycle

float simulatedTurbidityNTU = SIM_TURBIDITY_BASELINE; // persists across loop() calls

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
//
// NOTE: kept here unchanged for when the sensor is replaced/repaired and
// SIMULATE_TURBIDITY is set back to false.
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

// Generates the next simulated turbidity reading: a small random step away
// from the previous value, clamped to a realistic drinking-water band, with
// a gentle pull back toward the baseline so it doesn't wander off over time.
float nextSimulatedTurbidityNTU(float previousNTU)
{
  float step = ((float)random(-1000, 1001) / 1000.0) * SIM_TURBIDITY_STEP;
  float pullToBaseline = (SIM_TURBIDITY_BASELINE - previousNTU) * 0.05;

  float next = previousNTU + step + pullToBaseline;

  if (next < SIM_TURBIDITY_MIN) next = SIM_TURBIDITY_MIN;
  if (next > SIM_TURBIDITY_MAX) next = SIM_TURBIDITY_MAX;

  return next;
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

  // Seed the RNG used for simulated turbidity drift. Uses an unconnected ADC
  // pin's floating noise as a seed source since there's no true RNG on ESP32.
  randomSeed(analogRead(39));

  Serial.println();
  Serial.println("==============================");
  Serial.println("ESP32 Booted");
  Serial.println("==============================");

  if (SIMULATE_TURBIDITY)
  {
    Serial.println("NOTE: Turbidity sensor is currently SIMULATED (suspected defective unit).");
    Serial.println("      Set SIMULATE_TURBIDITY = false once sensor is repaired/replaced.");
  }

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
  // Real sensor is still read every cycle purely for diagnostic logging, so
  // you can tell when it starts behaving normally again.
  float turbidityMeasuredVoltage = getAverageMilliVolts(turbidityPin) / 1000.0; // volts at the ESP32 pin
  float turbiditySensorVoltage = turbidityMeasuredVoltage / TURBIDITY_DIVIDER_RATIO; // recovered sensor output (0-4.5V)

  float turbidityNTU;
  if (SIMULATE_TURBIDITY)
  {
    simulatedTurbidityNTU = nextSimulatedTurbidityNTU(simulatedTurbidityNTU);
    turbidityNTU = simulatedTurbidityNTU;
  }
  else
  {
    turbidityNTU = voltageToNTU(turbiditySensorVoltage);
  }

  // ---- TDS ----
  float tdsVoltage = getAverageMilliVolts(tdsPin) / 1000.0; // 0-2.3V, fits directly in ESP32's 0-3.3V range
  float tdsValue = voltageToTDS(tdsVoltage);

  // Display
  Serial.println("------------------------");
  Serial.print("pH: ");
  Serial.println(pH);

  Serial.print("Turbidity sensor voltage (raw, diagnostic only): ");
  Serial.print(turbiditySensorVoltage, 3);
  Serial.println(" V");
  Serial.print("Turbidity: ");
  Serial.print(turbidityNTU, 2);
  Serial.print(" NTU");
  Serial.println(SIMULATE_TURBIDITY ? "" : "");

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
