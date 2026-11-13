#!/bin/sh
# Reference chain-install for the RKNN conversion environment (Linux x86_64, python3.10).
# Creates a venv with: torch CPU -> rknn-toolkit2 2.3.2 -> airockchip/ultralytics_yolo11 fork.
# Customize:
#   VENV  = target venv path
#   LOGS  = log dir
#   FORK  = local clone of https://github.com/airockchip/ultralytics_yolo11
# Notes from the original build (see RKNN-CONVERT-REPORT.md "踩坑记录"):
#   * CPU torch is enough (conversion does not need a GPU)
#   * MUST pin onnx==1.15.0 (rknn-toolkit2 2.3.2 breaks with newer onnx: onnx.mapping removed)
#   * pip index below is the Tsinghua mirror; swap for your preferred index
set -e
VENV=${VENV:?set VENV=/path/to/rknn-venv}
LOGS=${LOGS:?set LOGS=/path/to/log-dir}
FORK=${FORK:?set FORK=/path/to/ultralytics_yolo11-clone}
IDX="-i https://pypi.tuna.tsinghua.edu.cn/simple"
mkdir -p "$LOGS"
PY=${PY:-python3.10}

[ -d "$VENV" ] || $PY -m venv "$VENV"
V=$VENV/bin

echo "== 1/4 torch CPU =="
$V/pip install $IDX torch==2.4.0+cpu torchvision==0.19.0+cpu \
  --extra-index-url https://download.pytorch.org/whl/cpu > "$LOGS/pip-torch-cpu.log" 2>&1

echo "== 2/4 rknn-toolkit2 + onnx pin =="
$V/pip install $IDX "rknn-toolkit2==2.3.2" "onnx==1.15.0" > "$LOGS/pip-rknn2.log" 2>&1

echo "== 3/4 airockchip ultralytics fork + deps =="
$V/pip install $IDX --no-deps "$FORK" > "$LOGS/pip-ultra.log" 2>&1
$V/pip install $IDX opencv-python pyyaml requests pillow scipy matplotlib \
  pandas seaborn psutil py-cpuinfo ultralytics-thop tqdm >> "$LOGS/pip-ultra.log" 2>&1

echo "== 4/4 import check =="
$V/python -c "import rknn, ultralytics, torch, torchvision; print('IMPORTS_OK', torch.__version__, ultralytics.__version__)"
echo CHAIN_ALL_DONE
