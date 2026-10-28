# Model Training & Annotation Pipeline (`training/`)

This directory provides the end-to-end tooling required to collect, annotate, augment, train, and export a custom YOLO object detection model fine-tuned for your specific IoT laboratory equipment.

---

## 1. Target Equipment Taxonomy

The pipeline is pre-configured to detect five core IoT laboratory classes:
- `0: 3d_printer` (Additive manufacturing machines, Prusa, Ender, Bambu Lab)
- `1: dell_monitor` (LCD displays, monitors on stands or monitor arms)
- `2: microcontroller` (ESP32, ESP8266, Arduino Uno/Nano, Raspberry Pi boards)
- `3: oscilloscope` (Digital benchtop oscilloscopes, signal generators)
- `4: soldering_station` (Soldering irons, temperature display bases, heat guns)

---

## 2. Step-by-Step Training Workflow

### Step 1: Capture In-Situ Dataset
To ensure zero domain gap, capture images directly with your camera setup:
```bash
# Capture using local webcam or video device
python training/scripts/capture_dataset.py --output-dir training/data/raw --camera-index 0

# Or trigger periodic capture directly from ESP32-CAM IP:
python training/scripts/capture_dataset.py --output-dir training/data/raw --source esp32_url --esp32-url http://192.168.1.100/capture --auto-interval 2.0
```
- Gather **300 to 500 images** capturing the lab under daytime lighting, evening fluorescent lights, and various angles.

---

### Step 2: Annotate with Label Studio or CVAT

1. **Install and run Label Studio locally**:
   ```bash
   pip install label-studio
   label-studio start
   ```
2. Create a new project named `IoT-Lab-Equipment`.
3. In **Labeling Setup**, select **Object Detection with Bounding Boxes** and enter the class names:
   ```xml
   <View>
     <Image name="image" value="$image"/>
     <RectangleLabels name="label" toName="image">
       <Label value="3d_printer" background="#10b981"/>
       <Label value="dell_monitor" background="#0ea5e9"/>
       <Label value="microcontroller" background="#f59e0b"/>
       <Label value="oscilloscope" background="#a855f7"/>
       <Label value="soldering_station" background="#f43f5e"/>
     </RectangleLabels>
   </View>
   ```
4. Upload all raw images from `training/data/raw/` and draw bounding boxes.
5. Click **Export** $\to$ Choose **YOLO** format.

---

### Step 3: Dataset Folder Structure

Extract the exported YOLO dataset into `training/data/` organized as follows:
```
training/data/
├── equipment.yaml
├── images/
│   ├── train/      (70% of images)
│   ├── val/        (20% of images)
│   └── test/       (10% of images)
└── labels/
    ├── train/      (.txt bounding box annotations)
    ├── val/        (.txt bounding box annotations)
    └── test/       (.txt bounding box annotations)
```

Each `.txt` label file contains rows in standard YOLO format:
```
<class-id> <center-x> <center-y> <width> <height>
```
*(All coordinates are normalized between 0.0 and 1.0).*

---

### Step 4: Fine-Tune the YOLO Model

Execute training using the included script:
```bash
# Train on local NVIDIA GPU (device 0):
python training/scripts/train.py --epochs 100 --batch 16 --device 0

# Or train on CPU if no dedicated GPU is available:
python training/scripts/train.py --epochs 50 --batch 8 --device cpu
```

When training completes:
- Training plots and confusion matrices are saved to `runs/detect/lab_equipment_run/`.
- The best weights checkpoint is automatically copied to `models/best.pt`.
- The FastAPI backend will load this model upon its next startup.

---

### Step 5: (Optional) Export to ONNX

To accelerate local CPU inference using ONNX Runtime:
```bash
python training/scripts/export_onnx.py --weights models/best.pt --half
```
