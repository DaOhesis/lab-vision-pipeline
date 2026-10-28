#pragma once

/**
 * Firmware Configuration & Network Credentials
 * Update these settings to match your local Wi-Fi and host IP.
 */

// Wi-Fi Network Credentials
#define WIFI_SSID           "YOUR_WIFI_SSID"
#define WIFI_PASSWORD       "YOUR_WIFI_PASSWORD"

// Local FastAPI Backend Host Configuration
#define BACKEND_HOST        "192.168.1.100"   // IP address of machine running FastAPI
#define BACKEND_PORT        8000
#define TELEMETRY_ENDPOINT  "/api/v1/telemetry/frame"

// Device Identity
#define DEVICE_ID           "esp32_cam_lab_01"

// Capture & Transmission Timing (in milliseconds)
#define FRAME_INTERVAL_MS   1500              // Snapshot transmission interval (1.5s)
#define WIFI_TIMEOUT_MS     15000             // Timeout for initial Wi-Fi connection
#define HTTP_TIMEOUT_MS     5000              // HTTP client request timeout
#define WATCHDOG_TIMEOUT_S  15                // FreeRTOS Task Watchdog timeout in seconds
