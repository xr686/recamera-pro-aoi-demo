"""RKNN FP16 conversion for hackster AOI models (rv1126b).
Usage: /tmp/recamera-rknn-env/bin/python convert_rknn.py <onnx> <out.rknn>
Based on moth8 proven pipeline: target rv1126b, mean 0 / std 255, no quantization (FP16)."""
import sys
from rknn.api import RKNN

SRC, DST = sys.argv[1], sys.argv[2]
rk = RKNN(verbose=False)
rk.config(target_platform="rv1126b", mean_values=[[0, 0, 0]], std_values=[[255, 255, 255]])
assert rk.load_onnx(model=SRC) == 0, "load_onnx fail"
assert rk.build(do_quantization=False) == 0, "build fail"
assert rk.export_rknn(DST) == 0, "export fail"
print("OK ->", DST)
