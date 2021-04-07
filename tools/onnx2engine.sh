#!/bin/sh
# trtexec --onnx=siamreppoints.backbone.onnx --explicitBatch --minShapes='input':1x3x127x127 --optShapes='input':1x3x255x255 --maxShapes='input':1x3x255x255 --shapes='input':1x3x255x255 --workspace=20480 --fp16 --saveEngine=siamreppoints.backbone.engine

# trtexec --onnx=siamreppoints.downsample2.onnx --explicitBatch --minShapes='input':1x512x15x15 --optShapes='input':1x512x31x31 --maxShapes='input':1x512x31x31 --shapes='input':1x512x31x31 --workspace=20480 --fp16 --saveEngine=siamreppoints.downsample2.engine
# trtexec --onnx=siamreppoints.downsample3.onnx --explicitBatch --minShapes='input':1x1024x15x15 --optShapes='input':1x1024x31x31 --maxShapes='input':1x1024x31x31 --shapes='input':1x1024x31x31 --workspace=20480 --fp16 --saveEngine=siamreppoints.downsample3.engine
# trtexec --onnx=siamreppoints.downsample4.onnx --explicitBatch --minShapes='input':1x2048x15x15 --optShapes='input':1x2048x31x31 --maxShapes='input':1x2048x31x31 --shapes='input':1x2048x31x31 --workspace=20480 --fp16 --saveEngine=siamreppoints.downsample4.engine

trtexec --onnx=siamreppoints.rpn2.onnx --workspace=20480 --fp16 --saveEngine=siamreppoints.rpn2.engine

# trtexec --onnx=pretrained/siamfc_alexnet_pruning_e50_z.onnx --workspace=1024 --fp16 --int8 --calib=pretrained/CalibrationTableSiamfc_pruning --saveEngine=pretrained/siamfc_alexnet_pruning_e50_z_int8.engine

# trtexec --onnx=siamreppoints.backbone.onnx --maxBatch=1 --workspace=1024 --fp16 --saveEngine=siamreppoints.backbone.engine