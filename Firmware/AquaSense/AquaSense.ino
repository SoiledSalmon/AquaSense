#include <WiFi.h>
#include <ThingSpeak.h>

//====================================================
// WiFi Credentials
//====================================================

const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

//====================================================
// ThingSpeak
//====================================================

unsigned long channelID = 0; // Replace with your Channel ID
const char* writeAPIKey = "YOUR_THINGSPEAK_WRITE_API_KEY";

WiFiClient client;

//====================================================
// Sensor Pins
//====================================================

const int phSensorPin = 34;
const int turbidityPin = 36;
const int tdsPin = 32;

//====================================================
// Constants
//====================================================

const float VREF = 3.3;
const int ADC_RESOLUTION = 4095;

const float waterTemperature = 29.0;

//====================================================
// TDS Median Filter
//====================================================

#define SCOUNT 30

int analogBuffer[SCOUNT];
int analogBufferTemp[SCOUNT];

int getMedianNum(int bArray[], int iFilterLen)
{
    int bTab[iFilterLen];

    for (int i = 0; i < iFilterLen; i++)
        bTab[i] = bArray[i];

    int temp;

    for (int j = 0; j < iFilterLen - 1; j++)
    {
        for (int i = 0; i < iFilterLen - j - 1; i++)
        {
            if (bTab[i] > bTab[i + 1])
            {
                temp = bTab[i];
                bTab[i] = bTab[i + 1];
                bTab[i + 1] = temp;
            }
        }
    }

    if ((iFilterLen & 1) > 0)
        return bTab[(iFilterLen - 1) / 2];
    else
        return (bTab[iFilterLen / 2] +
                bTab[iFilterLen / 2 - 1]) / 2;
}

//====================================================
// Average ADC Reading
//====================================================

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

//====================================================
// pH Calibration
//====================================================

float voltageTopH(float voltage)
{
    float m = -1.095;
    float b = 9.7375;

    return (m * voltage + b);
}

//====================================================
// TDS Calculation
//====================================================

float calculateTDS(int adcValue, float temperature)
{
    float voltage = adcValue * VREF / ADC_RESOLUTION;

    float compensationCoefficient =
        1.0 + 0.02 * (temperature - 25.0);

    float compensationVoltage =
        voltage / compensationCoefficient;

    float tds =
        (133.42 * compensationVoltage * compensationVoltage * compensationVoltage
        -255.86 * compensationVoltage * compensationVoltage
        +857.39 * compensationVoltage)
        *0.5;

    return tds;
}

//====================================================
// Setup
//====================================================

void setup()
{
    Serial.begin(115200);
    delay(2000);

    Serial.println();
    Serial.println("=======================================");
    Serial.println("      AquaSense ESP32 Starting");
    Serial.println("=======================================");

    analogReadResolution(12);
    analogSetAttenuation(ADC_11db);

    WiFi.mode(WIFI_STA);
    WiFi.disconnect(true);

    delay(1000);

    Serial.print("Connecting to WiFi : ");
    Serial.println(ssid);

    WiFi.begin(ssid, password);

    int attempts = 0;

    while (WiFi.status() != WL_CONNECTED && attempts < 20)
    {
        Serial.print(".");
        delay(1000);
        attempts++;
    }

    if (WiFi.status() == WL_CONNECTED)
    {
        Serial.println();
        Serial.println("WiFi Connected!");

        Serial.print("IP Address : ");
        Serial.println(WiFi.localIP());

        ThingSpeak.begin(client);
    }
    else
    {
        Serial.println();
        Serial.println("WiFi Connection Failed!");
    }
}

void loop()
{
    //=========================================
    // WiFi Reconnect
    //=========================================

    if (WiFi.status() != WL_CONNECTED)
    {
        Serial.println("\nWiFi Lost... Reconnecting");

        WiFi.disconnect();
        WiFi.begin(ssid, password);

        int retry = 0;

        while (WiFi.status() != WL_CONNECTED && retry < 10)
        {
            delay(1000);
            Serial.print(".");
            retry++;
        }

        if (WiFi.status() == WL_CONNECTED)
            Serial.println("\nReconnected!");
        else
            Serial.println("\nReconnect Failed");
    }

    //=========================================
    // pH
    //=========================================

    int phRaw = getAverageReading(phSensorPin);

    float phVoltage =
        phRaw * VREF / ADC_RESOLUTION;

    float pH = voltageTopH(phVoltage);

    //=========================================
    // Turbidity
    //=========================================

    int turbidityRaw = getAverageReading(turbidityPin);

    float turbidityPercent =
        ((4095.0 - turbidityRaw) / 4095.0) * 100.0;

    turbidityPercent =
        constrain(turbidityPercent, 0.0, 100.0);

    //=========================================
    // TDS (Median Filter)
    //=========================================

    for (int i = 0; i < SCOUNT; i++)
    {
        analogBuffer[i] = analogRead(tdsPin);
        delay(20);
    }

    for (int i = 0; i < SCOUNT; i++)
    {
        analogBufferTemp[i] = analogBuffer[i];
    }

    int tdsADC = getMedianNum(analogBufferTemp, SCOUNT);

    float voltage = tdsADC * VREF / ADC_RESOLUTION;

    float compensationCoefficient = 1.0 + 0.02 * (waterTemperature - 25.0);

    float compensationVoltage = voltage / compensationCoefficient;

    float tds = calculateTDS(tdsADC, waterTemperature);

    //=========================================
    // Serial Monitor
    //=========================================

    Serial.println();
    Serial.println("=======================================");

    Serial.print("pH               : ");
    Serial.println(pH, 2);

    Serial.print("pH Voltage       : ");
    Serial.print(phVoltage, 3);
    Serial.println(" V");

    Serial.print("Turbidity        : ");
    Serial.print(turbidityPercent, 1);
    Serial.println(" %");

    Serial.print("Water Temp       : ");
    Serial.print(waterTemperature, 1);
    Serial.println(" C");

    Serial.print("TDS ADC          : ");
    Serial.println(tdsADC);

    Serial.print("TDS Voltage      : ");
    Serial.print(voltage, 3);
    Serial.println(" V");

    Serial.print("Comp Voltage     : ");
    Serial.print(compensationVoltage, 3);
    Serial.println(" V");

    Serial.print("TDS              : ");
    Serial.print(tds, 1);
    Serial.println(" ppm");

    Serial.println("=======================================");

    //=========================================
    // ThingSpeak Upload
    //=========================================

    if (WiFi.status() == WL_CONNECTED)
    {
        ThingSpeak.setField(1, pH);
        ThingSpeak.setField(2, turbidityPercent);
        ThingSpeak.setField(3, tds);

        int response =
            ThingSpeak.writeFields(channelID,
                                   writeAPIKey);

        if (response == 200)
        {
            Serial.println("ThingSpeak Upload Successful");
        }
        else
        {
            Serial.print("ThingSpeak Error : ");
            Serial.println(response);
        }
    }
    else
    {
        Serial.println("Upload Skipped (No WiFi)");
    }

    delay(15000);
}

