# RKNN-CONVERT-REPORT — Edge-Ai-Vision-Inspection → rv1126b

> 日期：2026-11-02 · 环境：容器内 /tmp/recamera-rknn-env（python3.10，torch 2.4.0+cpu，rknn-toolkit2 2.3.2，airockchip/ultralytics_yolo11 fork 8.3.9）
> 结论：**4/4 stage 全部转换成功（FP16，未量化）**，产物为各 stage 的 `.rknn` 文件

## 转换结果

| 模型 | 源权重 | 输入 | 输出结构 | .rknn 大小 | 结果 |
|---|---|---|---|---|---|
| s1_cls（stage1 占用分类） | Slot Occuppancy Detection/runs/train/weights/best.pt (yolo11n-cls) | 1×3×**224**×224 | 1×3（Empty/PCB/PCBA 得分） | 3.9MB | ✅ |
| s2_pcb（stage2 裸板缺陷） | PCB Inspection/runs/train/weights/best.pt (yolo11s) | 1×3×640×640 | 9 输出 = 3 尺度×[DFL box 64ch, cls 1ch(Issue), obj 1ch] | 20.6MB | ✅ |
| s3a_big（stage3A 大元件 12 类） | Big Components Inspection/runs/train/weights/best.pt (yolo11n) | 1×3×640×640 | 9 输出，cls 12ch | 6.7MB | ✅ |
| s3b_small（stage3B 小元件 26 类） | Small Componets Inspection/runs/train_clean/weights/best.pt (yolo11n) | 1×3×640×640 | 9 输出，cls 26ch | 6.7MB | ✅ |

- 参数：`target_platform="rv1126b"`, mean 0/std 255, `do_quantization=False`（FP16），与板上 librknnrt 2.3.2 版本匹配（moth8 已验证的同款管线）
- detect 三件套输出布局与 moth8 `DetectDecoder` 完全一致，板端解码逻辑可直接复用
- s1 分类输出为 (1,3) 单输出，argmax 即得 Empty/PCB/PCBA；无 NMS/DFL 解码

## 量化数据集需求（若后续要 INT8）
- FP16 本次未用量化数据集；仓库自带各 stage 数据集可做 INT8 校准：
  - stage1: `Slot Occuppancy Detection/{train,test}/{Empty,PCB,PCBA}`（105 张）
  - stage2: `PCB Inspection/yolo_dataset{,_consistent}`（112 张）
  - stage3A: `Big Components Inspection/dataset`（131 张）
  - stage3B: `Small Componets Inspection/yolo_dataset`（139 张）
- ⚠️ 图片量偏少（百级），INT8 校准建议每类 ≥50 张、必要时增广；FP16 更稳妥

## .eim 模型（Edge Impulse）处理结论
- 4 个 `.eim`（slot-occupancy/pcb-inspection/big-/small-components-inspection.eim）为 Edge Impulse **BYOM + EON Compiler 针对 UNO Q (QRB2210) 的专有编译产物，不可逆、无法转 RKNN**——已如实记录，不走此路
- **替代路径已达成**：仓库自带全部 .pt 训练权重，直接经 Rockchip fork export + rknn-toolkit2 转换成功（上表），无需重训
- 若需彻底重训（如换自有数据集）：用仓库 YOLO 数据集 + ultralytics yolo11（cls 用 yolo11n-cls），流程同 moth8

## 踩坑记录（复刻环境必看）
1. **磁盘**：容器 / 曾 99% 满，CUDA torch 全家桶（~4GB）装不下 → 用 **CPU 版 torch**（`torch==2.4.0+cpu --index-url https://download.pytorch.org/whl/cpu --extra-index-url 清华`，仅 ~200MB wheel）即可，rknn-toolkit2 转换不吃 GPU
2. **onnx 版本坑**：rknn-toolkit2 2.3.2 依赖解析会装 onnx 1.23，但 `load_onnx` 用了已被移除的 `onnx.mapping` → 必须 **`pip install onnx==1.15.0`** 降级（本次 4 连败的真因）
3. python3.11 容器内缺 ensurepip 且 externally-managed → 用 `~/.local/bin/python3.10 -m venv`
4. 后台任务必须 `setsid nohup`（exec 会话清理会 SIGTERM 进程组，杀过两次链式安装）
5. pytorch cpu index 缺构建依赖（flit_core）→ 加 `--extra-index-url` 清华源
6. 重复 run 权重 md5 相同（train=train_consistent=weights 发布版），每 stage 实际只有 1 份有效权重

## 板端部署提示（未执行，留给下一阶段）
- 上板需实测：模拟器无法推理 load_rknn 产物（需 target），精度验证需连板（rknnlite + 真实图片对比 ONNX CPU 推理输出）
- stage1 是 224 输入，与其余 640 不同，manifest shape 要分开写
- 原项目管线逻辑（webcam_inspect.py / bms_eim_vision_inspection.py）可参考移植：占用分类 → 分流裸板/PCBA → 缺陷/元件核验
