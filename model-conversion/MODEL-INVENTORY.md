# MODEL-INVENTORY — Edge-Ai-Vision-Inspection (BMS PCB AOI)

> 仓库：MukeshSankhla/Edge-Ai-Vision-Inspection @ main（2026-11-02 下载，zip 824MB，解压后 944MB，869 entries）
> 解压位置：`/tmp/aoi-repo/Edge-Ai-Vision-Inspection-main/`
> 目标平台：Arduino UNO Q（QRB2210），模型经 Edge Impulse BYOM 打包为 .eim（EON 编译）
> 项目为 6 槽旋转台 AOI：stage1 判占用 → 裸板走 stage2 缺陷检测 / PCBA 走 stage3A+3B 元件装配核验

## 总览（4 个 stage，全部自带训练权重 .pt + ONNX + 数据集）

| Stage | 目录 | 任务 | 架构 | imgsz | 类别 | 权重 | ONNX | .eim |
|---|---|---|---|---|---|---|---|---|
| 1 | Slot Occuppancy Detection | classify | **yolo11n-cls**（50ep, batch8） | **224** | 3: Empty/PCB/PCBA | runs/train/weights/best.pt (3.19MB) | weights/best.onnx (6.17MB) | slot-occupancy.eim (19.6MB) |
| 2 | PCB Inspection | detect | **yolo11s**（100ep, batch4） | 640 | 1: Issue | 3 个 run 各有 best.pt (19.16MB) | weights/best.onnx (37.93MB) | pcb-inspection.eim (51.6MB) |
| 3A | Big Components Inspection | detect | **yolo11n**（80ep, batch8） | 640 | 12: C1A/C1N/C2A/C2N/IA/IN/PA/PN/SA/SN/UA/UN | runs/train/weights/best.pt (5.46MB) | weights/best.onnx (10.61MB) | big-components-inspection.eim (24.2MB) |
| 3B | Small Componets Inspection | detect | **yolo11n**（100ep, batch8） | 640 | 26: C1-C7/L1-L2/R1/R3-R5 各 A(在位)/N(缺失) | runs/train_clean + runs/train best.pt (5.47MB) | weights/best.onnx (10.62MB) | small-components-inspection.eim (58.4MB) |

## 明细

### Stage1 · Slot Occuppancy Detection（占用分类）
- `runs/train/weights/best.pt` / `last.pt`（3,189,762 B）— yolo11n-cls 训练产物（task: classify, model: yolo11n-cls.pt）
- `weights/best.onnx` = `runs/train/weights/best.onnx`（6,166,217 B，同尺寸）
- `weights/slot-occupancy.eim`（19,583,488 B）— Edge Impulse EON 编译二进制（BYOM），**专有格式不可转 RKNN**，仅参考
- 数据集：`train/{Empty,PCB,PCBA}`、`test/{...}`（该目录树共 105 张图）；`labels.txt`、makesense 标注 csv
- ⚠️ 无 data.yaml（分类任务直接按目录名）

### Stage2 · PCB Inspection（裸板表面缺陷，单类 Issue）
- 3 个训练 run：`runs/train`、`runs/train_consistent`、`runs/train_tuned`（各含 best.pt/last.pt 19,160,794 B + best.onnx ~37.93MB）
- `weights/best.onnx`（37,928,356 B）与 train/train_consistent 尺寸一致（train_tuned 为 37,928,344 B，略异）→ **发布版 ONNX 来自 train 或 train_consistent**
- 训练配置：yolo11s.pt 起步，100ep，imgsz 640；`data.yaml`（names: 0: Issue）、`data_consistent.yaml`
- 数据集：`yolo_dataset/`、`yolo_dataset_consistent/`（112 张图）；weights/ 下无 .pt（.pt 只在 runs/）
- `pcb-inspection.eim`（51,553,456 B）×2（另拷贝在 BMS EIM Vision Inspection/models/）

### Stage3A · Big Components Inspection（大元件装配核验，12 类）
- `runs/train/weights/best.pt`（5,457,306 B）、`weights/best.onnx`（10,613,312 B）
- 基座权重（非训练产物）：`yolo11n.pt`（5,613,764 B）、`weights/yolo26n.pt`（5,544,453 B，新版 ultralytics 基座）
- `data.yaml` 12 类（A=Assembled 在位 / N=Not 缺失，C1/C2 电容、I 电感?、P 电源IC、S 开关、U USB-C 等）；`dataset/`（131 张图）
- `big-components-inspection.eim`（24,242,472 B）×2
- 辅助脚本：train.py、export_onnx.py、predict.py、convert_makesense_to_yolo.py

### Stage3B · Small Componets Inspection（小元件 0805，26 类）
- 2 个 run：`runs/train`、`runs/train_clean`（best.pt 5,465,626 B）；`weights/best.onnx`（10,624,428 B）与 train_clean/train 尺寸一致
- `data.yaml` 26 类（C1-C7 电容、L1-L2 电感、R1/R3-R5 电阻，各分 A/N）；`yolo_dataset/`（139 张图）
- `small-components-inspection.eim`（58,436,408 B）×2
- ⚠️ runs/train 无 args.yaml（只有 train_clean 的）；train_clean: yolo11n.pt, 100ep, imgsz640

### BMS EIM Vision Inspection（生产运行时）
- `models/` = 4 个 .eim 的副本（上表已计）；`bms_eim_vision_inspection.py` 主管线（edge-impulse-sdk Python）；arduino_firmware/（舵机转盘）
- .eim 为 Edge Impulse EON Compiler 针对 QRB2210 的专有编译产物，**无法逆向转 RKNN**；替代路径 = 直接用 .pt/.onnx 转（见 RKNN-CONVERT-REPORT.md）

### 其它
- `Images/`（220MB）文档配图/GIF；`CAD/`（4MB）Fusion360 结构件
- 所有 data.yaml 中 path 为作者 Windows 本机绝对路径（C:/Users/MAKERBRAINS/...），复训需改

## RKNN 转换候选结论
- ✅ 可转：4 个 stage 的 YOLO .pt（yolo11 系）→ Rockchip ultralytics fork export format=rknn → rknn-toolkit2 2.3.2 → rv1126b
- ❌ 不可转：.eim ×4（EON 专有）
- stage1 为分类模型（imgsz 224，无检测头），RKNN 转换路径与 detect 不同（无 DFL/NMS 解码，输出 softmax 3 类），需单独验证
