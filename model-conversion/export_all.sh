#!/bin/sh
# Export AOI stage weights to RKNN-compatible ONNX via the Rockchip ultralytics fork.
# Customize these two paths for your machine:
#   REPO  = checkout of MukeshSankhla/Edge-Ai-Vision-Inspection
#   WORK  = scratch dir for exported artifacts
#   RKENV = venv containing rknn-toolkit2 + airockchip/ultralytics_yolo11 (see chain_install.sh)
set -e
REPO=${REPO:?set REPO=/path/to/Edge-Ai-Vision-Inspection}
WORK=${WORK:?set WORK=/path/to/export-dir}
P=${RKENV:?set RKENV=/path/to/rknn-venv}/bin

mkdir -p "$WORK"
cd "$WORK"
# .pt files are copied to workdir first so repo originals are never overwritten.
cp "$REPO/Slot Occuppancy Detection/runs/train/weights/best.pt" s1_cls.pt
cp "$REPO/PCB Inspection/runs/train/weights/best.pt" s2_pcb.pt
cp "$REPO/Big Components Inspection/runs/train/weights/best.pt" s3a_big.pt
cp "$REPO/Small Componets Inspection/runs/train_clean/weights/best.pt" s3b_small.pt

# stage1: yolo11n-cls (classify, imgsz 224)
$P/yolo export model=s1_cls.pt format=rknn name=rv1126b imgsz=224 device=cpu > s1.log 2>&1
# stage2: yolo11s detect 1cls (Issue)
$P/yolo export model=s2_pcb.pt format=rknn name=rv1126b imgsz=640 device=cpu > s2.log 2>&1
# stage3A: yolo11n detect 12cls
$P/yolo export model=s3a_big.pt format=rknn name=rv1126b imgsz=640 device=cpu > s3a.log 2>&1
# stage3B: yolo11n detect 26cls
$P/yolo export model=s3b_small.pt format=rknn name=rv1126b imgsz=640 device=cpu > s3b.log 2>&1
echo EXPORT_ALL_DONE
ls -la "$WORK"
