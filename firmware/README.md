# ESP32-CAM C++ Firmware (`firmware/`)

This directory contains the edge ingestion firmware for the **AI-Thinker ESP32-CAM** running on the ESP32-D0WDQ6 chip with an OmniVision OV2640 sensor.

---

## 1. Hardware Pinout & FTDI Programmer Wiring

The ESP32-CAM module lacks an onboard USB-to-UART chip. To flash and debug the board, connect an **FTDI USB-to-TTL programmer** as follows:

| FTDI Programmer Pin | ESP32-CAM Pin | Notes |
| :--- | :--- | :--- |
| **5V / VCC** | **5V** | **Crucial:** Power with 5V (NOT 3.3V) to prevent sensor brownout resets. |
| **GND** | **GND** | Common ground reference. |
| **TX** | **U0R (GPIO 3)** | Serial RX on ESP32. |
| **RX** | **U0T (GPIO 1)** | Serial TX on ESP32. |
| **GND (Jumper)** | **GPIO 0** | **Connect GPIO 0 to GND only when flashing!** Disconnect for normal boot. |

> [!IMPORTANT]
> - Connect a **100 µF to 470 µF capacitor** between the `5V` and `GND` pins on the ESP32-CAM to absorb current spikes when Wi-Fi and the camera sensor power on simultaneously.
> - Ensure your FTDI programmer provides at least **500 mA** of current. Low-power USB hubs can trigger continuous reboot cycles.

---

## 2. Configuration Setup

Before building, open [`include/config.h`](include/config.h) and set your local credentials:

```cpp
// Wi-Fi Network Credentials
#define WIFI_SSID           "Your_WiFi_Network"
#define WIFI_PASSWORD       "Your_WiFi_Password"

// Host running FastAPI backend
#define BACKEND_HOST        "192.168.1.15"       // Replace with your computer's local LAN IP
#define BACKEND_PORT        8000
#define TELEMETRY_ENDPOINT  "/api/v1/telemetry/frame"

// Capture interval in milliseconds
#define FRAME_INTERVAL_MS   1500                 // Transmit a snapshot every 1.5 seconds
```

---

## 3. Building & Flashing via PlatformIO

### Prerequisites
- [VS Code with PlatformIO IDE Extension](https://platformio.org/) **or** PlatformIO Core CLI:
  ```bash
  pip install platformio
  ```

### Build & Upload Steps
1. Connect **GPIO 0 to GND** with a jumper wire.
2. Plug the FTDI programmer into your computer's USB port.
3. Press the **RST** button on the back of the ESP32-CAM once to enter flashing mode.
4. Execute upload:
   ```bash
   cd firmware
   pio run --target upload
   ```
5. **Remove the jumper wire between GPIO 0 and GND**.
6. Press the **RST** button again to boot into normal operating mode.
7. Open the Serial Monitor to observe live logs:
   ```bash
   pio device monitor -b 115200
   ```

---

## 4. Key Firmware Architecture Features

- **PSRAM Buffer Allocation**: Detects 4MB external PSRAM at boot and allocates dual frame buffers (`fb_count = 2`) via DMA.
- **Sensor Calibration**: Pre-configured indoor laboratory exposure, auto white-balance gains, and contrast curves for clean equipment edge detection.
- **Brownout Suppression**: Disables internal software brownout trips during fast Wi-Fi bursts.
- **Hardware Task Watchdog**: Initialized to 15 seconds via `esp_task_wdt`; automatically reboots the module if the camera DMA pipeline freezes.
- **Network Ingestion**: Sends raw JPEG frames with timing and metadata headers (`X-Device-Id`, `X-Timestamp-Ms`, `X-Frame-Index`) to FastAPI.
