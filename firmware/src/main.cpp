#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include "esp_camera.h"
#include "esp_task_wdt.h"
#include "soc/soc.h"
#include "soc/rtc_cntl_reg.h"

#include "camera_pins.h"
#include "config.h"

static unsigned long lastFrameTime = 0;
static uint32_t frameSequence = 0;

void setStatusLed(bool on) {
    // Red status LED on GPIO 33 is active LOW
    digitalWrite(STATUS_LED_PIN, on ? LOW : HIGH);
}

bool initCamera() {
    camera_config_t config;
    config.ledc_channel = LEDC_CHANNEL_0;
    config.ledc_timer = LEDC_TIMER_0;
    config.pin_d0 = Y2_GPIO_NUM;
    config.pin_d1 = Y3_GPIO_NUM;
    config.pin_d2 = Y4_GPIO_NUM;
    config.pin_d3 = Y5_GPIO_NUM;
    config.pin_d4 = Y6_GPIO_NUM;
    config.pin_d5 = Y7_GPIO_NUM;
    config.pin_d6 = Y8_GPIO_NUM;
    config.pin_d7 = Y9_GPIO_NUM;
    config.pin_xclk = XCLK_GPIO_NUM;
    config.pin_pclk = PCLK_GPIO_NUM;
    config.pin_vsync = VSYNC_GPIO_NUM;
    config.pin_href = HREF_GPIO_NUM;
    config.pin_sccb_sda = SIOD_GPIO_NUM;
    config.pin_sccb_scl = SIOC_GPIO_NUM;
    config.pin_pwdn = PWDN_GPIO_NUM;
    config.pin_reset = RESET_GPIO_NUM;
    config.xclk_freq_hz = 20000000;
    config.pixel_format = PIXFORMAT_JPEG;
    config.grab_mode = CAMERA_GRAB_LATEST;

    // Check for PSRAM availability
    if (psramFound()) {
        Serial.printf("[CAM] PSRAM detected! Size: %d KB\n", ESP.getPsramSize() / 1024);
        config.frame_size = FRAMESIZE_SVGA;  // 800x600 resolution
        config.jpeg_quality = 12;            // 10-12 gives crisp frames with optimal bandwidth
        config.fb_count = 2;                 // Double buffering via DMA in PSRAM
        config.fb_location = CAMERA_FB_IN_PSRAM;
    } else {
        Serial.println("[CAM] WARNING: No PSRAM detected. Falling back to VGA / Single buffer.");
        config.frame_size = FRAMESIZE_VGA;   // 640x480 resolution
        config.jpeg_quality = 15;
        config.fb_count = 1;
        config.fb_location = CAMERA_FB_IN_DRAM;
    }

    esp_err_t err = esp_camera_init(&config);
    if (err != ESP_OK) {
        Serial.printf("[CAM] ERROR: Camera init failed with code 0x%x\n", err);
        return false;
    }

    sensor_t* s = esp_camera_sensor_get();
    if (s != nullptr) {
        // Sensor calibration for indoor lab lighting
        s->set_brightness(s, 1);     // -2 to 2
        s->set_contrast(s, 1);       // -2 to 2
        s->set_saturation(s, 0);     // -2 to 2
        s->set_whitebal(s, 1);       // 0 = disable , 1 = enable
        s->set_awb_gain(s, 1);       // 0 = disable , 1 = enable
        s->set_wb_mode(s, 0);        // 0 to 4 - 0: Auto, 1: Sunny, 2: Cloudy, 3: Office, 4: Home
        s->set_exposure_ctrl(s, 1);  // 0 = disable , 1 = enable
        s->set_aec2(s, 0);           // 0 = disable , 1 = enable
        s->set_gain_ctrl(s, 1);      // 0 = disable , 1 = enable
        s->set_agc_gain(s, 0);       // 0 to 30
        s->set_gainceiling(s, (gainceiling_t)2);  // 0 to 6
        s->set_bpc(s, 1);            // 0 = disable , 1 = enable
        s->set_wpc(s, 1);            // 0 = disable , 1 = enable
        s->set_raw_gma(s, 1);        // 0 = disable , 1 = enable
        s->set_lenc(s, 1);           // 0 = disable , 1 = enable
        s->set_hmirror(s, 0);        // 0 = disable , 1 = enable
        s->set_vflip(s, 0);          // 0 = disable , 1 = enable
        s->set_dcw(s, 1);            // 0 = disable , 1 = enable
    }

    Serial.println("[CAM] Camera successfully initialized and calibrated.");
    return true;
}

void connectWiFi() {
    Serial.printf("[WIFI] Connecting to SSID: %s\n", WIFI_SSID);
    WiFi.mode(WIFI_STA);
    WiFi.setSleep(false); // Disable Wi-Fi power saving for stable streaming
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    unsigned long startAttemptTime = millis();
    while (WiFi.status() != WL_CONNECTED && millis() - startAttemptTime < WIFI_TIMEOUT_MS) {
        setStatusLed(true);
        delay(100);
        setStatusLed(false);
        delay(150);
        Serial.print(".");
    }

    if (WiFi.status() == WL_CONNECTED) {
        Serial.println("\n[WIFI] Connected successfully!");
        Serial.printf("[WIFI] IP Address: %s\n", WiFi.localIP().toString().c_str());
        Serial.printf("[WIFI] Signal Strength (RSSI): %d dBm\n", WiFi.RSSI());
        setStatusLed(true); // Solid status LED when connected
    } else {
        Serial.println("\n[WIFI] ERROR: Connection timed out. Will retry in loop.");
        setStatusLed(false);
    }
}

bool transmitFrame(camera_fb_t* fb) {
    if (WiFi.status() != WL_CONNECTED) {
        Serial.println("[HTTP] Wi-Fi lost. Attempting reconnection...");
        connectWiFi();
        if (WiFi.status() != WL_CONNECTED) return false;
    }

    HTTPClient http;
    char serverUrl[128];
    snprintf(serverUrl, sizeof(serverUrl), "http://%s:%d%s", BACKEND_HOST, BACKEND_PORT, TELEMETRY_ENDPOINT);

    http.begin(serverUrl);
    http.setTimeout(HTTP_TIMEOUT_MS);
    http.addHeader("Content-Type", "image/jpeg");
    http.addHeader("X-Device-Id", DEVICE_ID);
    http.addHeader("X-Frame-Index", String(frameSequence));
    http.addHeader("X-Timestamp-Ms", String(millis()));

    unsigned long postStart = millis();
    int httpResponseCode = http.POST(fb->buf, fb->len);
    unsigned long duration = millis() - postStart;

    if (httpResponseCode > 0) {
        Serial.printf("[HTTP] Frame #%u (%u bytes) posted. HTTP Code: %d (%lu ms)\n", 
                      frameSequence, fb->len, httpResponseCode, duration);
        http.end();
        return (httpResponseCode == 200 || httpResponseCode == 201);
    } else {
        Serial.printf("[HTTP] ERROR: Frame POST failed, error: %s (after %lu ms)\n", 
                      http.errorToString(httpResponseCode).c_str(), duration);
        http.end();
        return false;
    }
}

void setup() {
    // Disable brownout detector to prevent reset on current surge
    WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0);

    Serial.begin(115200);
    delay(1000);
    Serial.println("\n==========================================");
    Serial.println("  IoT Lab Vision - ESP32-CAM Ingestion    ");
    Serial.println("==========================================");

    pinMode(STATUS_LED_PIN, OUTPUT);
    pinMode(FLASH_LED_PIN, OUTPUT);
    digitalWrite(FLASH_LED_PIN, LOW); // Keep bright white flash OFF by default
    setStatusLed(false);

    // Initialize Camera Sensor
    if (!initCamera()) {
        Serial.println("[FATAL] Camera initialization failed. Halting.");
        while (true) {
            setStatusLed(true);
            delay(200);
            setStatusLed(false);
            delay(200);
        }
    }

    // Connect to local Wi-Fi
    connectWiFi();

    // Initialize Task Watchdog Timer
    esp_task_wdt_init(WATCHDOG_TIMEOUT_S, true);
    esp_task_wdt_add(NULL); // Subscribe current Arduino task to watchdog
    Serial.printf("[WDT] Task watchdog configured (%d seconds).\n", WATCHDOG_TIMEOUT_S);
}

void loop() {
    // Reset watchdog timer
    esp_task_wdt_reset();

    unsigned long now = millis();
    if (now - lastFrameTime >= FRAME_INTERVAL_MS) {
        lastFrameTime = now;

        // Capture frame from camera
        camera_fb_t* fb = esp_camera_fb_get();
        if (!fb) {
            Serial.println("[CAM] ERROR: Failed to acquire camera frame buffer.");
            delay(100);
            return;
        }

        // Transmit frame to FastAPI backend
        frameSequence++;
        transmitFrame(fb);

        // Always return buffer to camera driver DMA ring
        esp_camera_fb_return(fb);
    }

    // Yield CPU time to allow background Wi-Fi tasks to process
    vTaskDelay(pdMS_TO_TICKS(10));
}
