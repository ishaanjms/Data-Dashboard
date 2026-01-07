#include <ESP8266WiFi.h>
#include <Adafruit_ADS1X15.h>
#include <math.h>

// ADS1115 Instances
Adafruit_ADS1115 ads1;  // Address 0x48
Adafruit_ADS1115 ads2;  // Address 0x49
Adafruit_ADS1115 ads3;  // Address 0x4A
Adafruit_ADS1115 ads4;  // Address 0x4B

const char* ssid = "KRC-PA";
const char* password = "parc8810@";
const char* server = "172.16.26.53";  // my Host IP
const int serverPort = 5176;  // my Port

WiFiClient client;

void setup() {
  Serial.begin(9600);

  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.println("Connecting to WiFi...");
  }
  Serial.println("Connected to WiFi");

  if (!ads1.begin(0x48)) Serial.println("ADS1115 #1 init failed");
  else Serial.println("ADS1115 #1 ready");

  if (!ads2.begin(0x49)) Serial.println("ADS1115 #2 init failed");
  else Serial.println("ADS1115 #2 ready");

  if (!ads3.begin(0x4A)) Serial.println("ADS1115 #3 init failed");
  else Serial.println("ADS1115 #3 ready");

  if (!ads4.begin(0x4B)) Serial.println("ADS1115 #4 init failed");
  else Serial.println("ADS1115 #4 ready");
}

void loop() {
  static unsigned long lastSendTime = 0;
  const unsigned long interval = 60000;  // 2 minutes

  if (millis() - lastSendTime >= interval) {
    lastSendTime = millis();

    float volt[16];

    for (int ch = 0; ch < 16; ch++) {
      int16_t adcValue = 0;

      if (ch < 4)
        adcValue = ads1.readADC_SingleEnded(ch);
      else if (ch < 8)
        adcValue = ads2.readADC_SingleEnded(ch - 4);
      else if (ch < 12)
        adcValue = ads3.readADC_SingleEnded(ch - 8);
      else
        adcValue = ads4.readADC_SingleEnded(ch - 12);

      volt[ch] = abs(adcValue * 0.1875);  // mV

      Serial.print("CH ");
      Serial.print(ch);
      Serial.print(" | ADC: ");
      Serial.print(adcValue);
      Serial.print(" | Voltage: ");
      Serial.print(volt[ch], 2);
      Serial.println(" mV");
    }

    // Build POST data with 16 labeled channels
    String postData = "";
    postData += "X1=" + String(volt[0], 2) + "&";
    postData += "X2=" + String(volt[1], 2) + "&";
    postData += "Y1=" + String(volt[2], 2) + "&";
    postData += "Y2=" + String(volt[3], 2) + "&";
    postData += "Z1=" + String(volt[4], 2) + "&";
    postData += "Z2=" + String(volt[5], 2) + "&";
    postData += "D1=" + String(volt[6], 2) + "&";
    postData += "D2=" + String(volt[7], 2) + "&";
    postData += "P1=" + String(volt[8], 2) + "&";
    postData += "P2=" + String(volt[9], 2) + "&";
    postData += "P3=" + String(volt[10], 2) + "&";
    postData += "P4=" + String(volt[11], 2) + "&";
    postData += "P5=" + String(volt[12], 2) + "&";
    postData += "EX1=" + String(volt[13], 2) + "&";
    postData += "EX2=" + String(volt[14], 2) + "&";
    postData += "EX3=" + String(volt[15], 2);

    Serial.print("Sending data: ");
    Serial.println(postData);

    if (client.connect(server, serverPort)) {
      Serial.println("✅ Connected to server\n");
      String url = "/api/sensor-data"; 

      client.print("POST " + url + " HTTP/1.1\r\n");
      client.print("Host: ");
      client.println(server);
      client.println("Connection: close");
      client.println("Content-Type: application/x-www-form-urlencoded");
      client.print("Content-Length: ");
      client.println(postData.length());
      client.println();
      client.print(postData);

      while (client.connected() || client.available()) {
        if (client.available()) {
          String line = client.readStringUntil('\n');
          Serial.println("Server: " + line);
        }
      }

      client.stop();
      Serial.println("✅ Data sent successfully.\n");
    } else {
      Serial.println("❌ Connection to server failed.\n");
      client.stop();
    }
  }
}

