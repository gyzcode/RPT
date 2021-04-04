#!/bin/sh
trtexec --onnx=siamreppoints.backbone.onnx --explicitBatch --minShapes='input':1x3x127x127 --optShapes='input':1x3x255x255 --maxShapes='input':1x3x255x255 --shapes='input':1x3x255x255 --workspace=20480 --fp16 --saveEngine=siamreppoints.backbone.engine

# trtexec --onnx=pretrained/siamfc_alexnet_pruning_e50_z.onnx --workspace=1024 --fp16 --int8 --calib=pretrained/CalibrationTableSiamfc_pruning --saveEngine=pretrained/siamfc_alexnet_pruning_e50_z_int8.engine

# trtexec --onnx=siamreppoints.backbone.onnx --maxBatch=1 --workspace=1024 --fp16 --saveEngine=siamreppoints.backbone.engine