from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os
import argparse

import sys
import cv2
import torch
import numpy as np

filepath = os.path.abspath(__file__)
filelocation = os.path.split(filepath)[0]
rootpath = os.path.dirname(filelocation) 
sys.path.append(rootpath)

from siamreppoints.core.config import cfg
from siamreppoints.models.model_builder import ModelBuilder
from siamreppoints.tracker.tracker_builder import build_tracker
from siamreppoints.utils.model_load import load_pretrain
from toolkit.datasets import DatasetFactory
from toolkit.utils.region import vot_overlap, vot_float2str
from siamreppoints.utils.bbox import get_axis_aligned_bbox
torch.set_num_threads(1)

os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"

parser = argparse.ArgumentParser(description='tracking demo')
parser.add_argument('--config', type=str, help='config file')
parser.add_argument('--snapshot', type=str, help='model name')
parser.add_argument('--dataset', default='VOT2018', type=str,
                    help='videos or image files')
parser.add_argument('--video', default='', type=str, 
                    help='eval one special video')
parser.add_argument('--vis', action='store_true', 
                    help='whether visualize result')
parser.add_argument('--gpu_id', default='not_set', type=str, help='gpu id')
args = parser.parse_args()

if args.gpu_id != 'not_set':
    os.environ['CUDA_VISIBLE_DEVICES'] = args.gpu_id

def main():
    # load config
    cfg.merge_from_file(args.config)

    cur_dir = os.path.dirname(os.path.realpath(__file__))
    dataset_root = os.path.join(cur_dir, '../testing_dataset', args.dataset)
    
    # create model
    model = ModelBuilder()

    # load model
    model = load_pretrain(model, args.snapshot).cuda().eval()

    # convert to onnx
    onnx_path = 'siamreppoints.backbone.onnx'
    if not os.path.exists(onnx_path):
        input_names = ['input']
        output_names = ['output']
        dummy_input = torch.randn(1, 3, 127, 127).cuda()
        dynamic_axes = {'input':{2:'width', 3:'height'}, 'output':{2:'width', 3:'height'}} #adding names for better debugging
        torch.onnx.export(model.backbone, dummy_input, onnx_path, verbose=True, input_names=input_names, output_names=output_names, dynamic_axes=dynamic_axes, opset_version=11)
    
    onnx_path = 'siamreppoints.downsample2.onnx'
    if not os.path.exists(onnx_path):
        input_names = ['input']
        output_names = ['output']
        dummy_input = torch.randn(1, 512, 15, 15).cuda()
        dynamic_axes = {'input':{2:'width', 3:'height'}, 'output':{2:'width', 3:'height'}} #adding names for better debugging
        torch.onnx.export(model.neck.downsample2, dummy_input, onnx_path, verbose=True, input_names=input_names, output_names=output_names, dynamic_axes=dynamic_axes, opset_version=11)

    onnx_path = 'siamreppoints.downsample3.onnx'
    if not os.path.exists(onnx_path):
        input_names = ['input']
        output_names = ['output']
        dummy_input = torch.randn(1, 1024, 15, 15).cuda()
        dynamic_axes = {'input':{2:'width', 3:'height'}, 'output':{2:'width', 3:'height'}} #adding names for better debugging
        torch.onnx.export(model.neck.downsample3, dummy_input, onnx_path, verbose=True, input_names=input_names, output_names=output_names, dynamic_axes=dynamic_axes, opset_version=11)

    onnx_path = 'siamreppoints.downsample4.onnx'
    if not os.path.exists(onnx_path):
        input_names = ['input']
        output_names = ['output']
        dummy_input = torch.randn(1, 2048, 15, 15).cuda()
        dynamic_axes = {'input':{2:'width', 3:'height'}, 'output':{2:'width', 3:'height'}} #adding names for better debugging
        torch.onnx.export(model.neck.downsample4, dummy_input, onnx_path, verbose=True, input_names=input_names, output_names=output_names, dynamic_axes=dynamic_axes, opset_version=11)

    # # maybe incorrect
    # onnx_path = 'siamreppoints.rpn2.onnx'
    # if not os.path.exists(onnx_path):
    #     input_names = ['input1', 'input2']
    #     output_names = ['output1', 'output2', 'output3']
    #     dummy_input = (torch.randn(1, 256, 7, 7).cuda(), torch.randn(1, 256, 31, 31).cuda())
    #     torch.onnx.export(model.rpn_head.rpn2, dummy_input, onnx_path, verbose=True, input_names=input_names, output_names=output_names, opset_version=11)

    # # maybe incorrect
    # onnx_path = 'siamreppoints.rpn3.onnx'
    # if not os.path.exists(onnx_path):
    #     input_names = ['input1', 'input2']
    #     output_names = ['output1', 'output2', 'output3']
    #     dummy_input = (torch.randn(1, 256, 7, 7).cuda(), torch.randn(1, 256, 31, 31).cuda())
    #     torch.onnx.export(model.rpn_head.rpn3, dummy_input, onnx_path, verbose=True, input_names=input_names, output_names=output_names, opset_version=11)

    # # maybe incorrect
    # onnx_path = 'siamreppoints.rpn4.onnx'
    # if not os.path.exists(onnx_path):
    #     input_names = ['input1', 'input2']
    #     output_names = ['output1', 'output2', 'output3']
    #     dummy_input = (torch.randn(1, 256, 7, 7).cuda(), torch.randn(1, 256, 31, 31).cuda())
    #     torch.onnx.export(model.rpn_head.rpn4, dummy_input, onnx_path, verbose=True, input_names=input_names, output_names=output_names, opset_version=11)

    # build tracker
    tracker = build_tracker(model)
    
    dataset = DatasetFactory.create_dataset(name=args.dataset, dataset_root=dataset_root, load_img=False)
    model_name = args.snapshot.split('/')[-1].split('.')[0]
    total_lost = 0
   
    if args.dataset in ['VOT2016', 'VOT2018', 'VOT2019']:
        # restart tracking
        for v_idx, video in enumerate(dataset):
            if args.video != '':
                if video.name != args.video:
                    continue
            frame_counter = 0
            lost_number = 0
            toc = 0
            pred_bboxes = []
            for idx, (img, gt_bbox) in enumerate(video):
                if len(gt_bbox) == 4:
                    gt_bbox = [gt_bbox[0], gt_bbox[1],
                       gt_bbox[0], gt_bbox[1]+gt_bbox[3]-1,
                       gt_bbox[0]+gt_bbox[2]-1, gt_bbox[1]+gt_bbox[3]-1,
                       gt_bbox[0]+gt_bbox[2]-1, gt_bbox[1]]
                tic = cv2.getTickCount()
                if idx == frame_counter:
                    cx, cy, w, h = get_axis_aligned_bbox(np.array(gt_bbox))
                    gt_bbox_ = [cx-(w-1)/2, cy-(h-1)/2, w, h]
                    tracker.init(img, gt_bbox_)
                    pred_bbox = gt_bbox_
                    pred_bboxes.append(1)
                    score = 0.0
                elif idx > frame_counter:
                    outputs = tracker.track(img)
                    pred_bbox = outputs['bbox']
                    score = outputs['best_score']
                    overlap = vot_overlap(pred_bbox, gt_bbox, (img.shape[1], img.shape[0]))
                    if overlap > 0:
                        # not lost
                        pred_bboxes.append(pred_bbox)
                    else:
                        # lost object
                        pred_bboxes.append(2)
                        frame_counter = idx + 5 # skip 5 frames
                        lost_number += 1
                else:
                    pred_bboxes.append(0)
                toc += cv2.getTickCount() - tic
                if idx == 0:
                   cv2.destroyAllWindows()
                if args.vis:
                # if False:
                    cv2.polylines(img, [np.array(gt_bbox, np.int).reshape((-1, 1, 2))],
                            True, (0, 255, 0), 3)
                   
                    bbox = list(map(int, pred_bbox))
                    cv2.rectangle(img, (bbox[0], bbox[1]),
                                  (bbox[0]+bbox[2], bbox[1]+bbox[3]), (0, 255, 255), 3)
                    cv2.putText(img, str(idx), (40, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
                    cv2.putText(img, str(lost_number), (40, 80), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                    
                    cv2.putText(img, str(score), (40, 120), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 255), 2)
                    cv2.imshow('img', img)
                    cv2.imshow(video.name, img)
                    cv2.waitKey(1)
            toc /= cv2.getTickFrequency()
            # save results
            video_path = os.path.join('results', args.dataset, model_name,
                    'baseline', video.name)
            if not os.path.isdir(video_path):
                os.makedirs(video_path)
            result_path = os.path.join(video_path, '{}_001.txt'.format(video.name))
            with open(result_path, 'w') as f:
                for x in pred_bboxes:
                    if isinstance(x, int):
                        f.write("{:d}\n".format(x))
                    else:
                        f.write(','.join([vot_float2str("%.4f", i) for i in x])+'\n')
            print('({:3d}) Video: {:12s} Time: {:4.1f}s Speed: {:3.1f}fps Lost: {:d}'.format(
                    v_idx+1, video.name, toc, idx / toc, lost_number))
            total_lost += lost_number
        print("{:s} total lost: {:d}".format(model_name, total_lost))
    else:
        # OPE tracking
        for v_idx, video in enumerate(dataset):
            toc = 0
            pred_bboxes = []
            scores = []
            track_times = []
            
            for idx, (img, gt_bbox) in enumerate(video):
                tic = cv2.getTickCount()
                if idx == 0:
                    cx, cy, w, h = get_axis_aligned_bbox(np.array(gt_bbox))
                    gt_bbox_ = [cx-(w-1)/2, cy-(h-1)/2, w, h]
                    tracker.init(img, gt_bbox_)
                    pred_bbox = gt_bbox_
                    scores.append(None)
                    if 'VOT2018-LT' == args.dataset:
                        pred_bboxes.append([1])
                    else:
                        pred_bboxes.append(pred_bbox)
                else:
                    outputs = tracker.track(img)
                    pred_bbox = outputs['bbox']
                    pred_bboxes.append(pred_bbox)
                    scores.append(outputs['best_score'])
                toc += cv2.getTickCount() - tic
                track_times.append((cv2.getTickCount() - tic)/cv2.getTickFrequency())
                if idx == 0:
                    cv2.destroyAllWindows()
                if True:
                    #import pdb
                    #pdb.set_trace()
                    gt_bbox = list(map(int, gt_bbox))
                    pred_bbox = list(map(int, pred_bbox))
                    cv2.rectangle(img, (gt_bbox[0], gt_bbox[1]),
                                  (gt_bbox[0]+gt_bbox[2], gt_bbox[1]+gt_bbox[3]), (0, 255, 0), 3)
                    cv2.rectangle(img, (pred_bbox[0], pred_bbox[1]),
                                  (pred_bbox[0]+pred_bbox[2], pred_bbox[1]+pred_bbox[3]), (0, 255, 255), 3)
                    cv2.putText(img, str(idx), (40, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
                  
                    cv2.imshow('show', img)
                    cv2.waitKey(1)
            toc /= cv2.getTickFrequency()
            # save results
            if 'VOT2018-LT' == args.dataset:
                video_path = os.path.join('results', args.dataset, model_name,
                        'longterm', video.name)
                if not os.path.isdir(video_path):
                    os.makedirs(video_path)
                result_path = os.path.join(video_path,
                        '{}_001.txt'.format(video.name))
                with open(result_path, 'w') as f:
                    for x in pred_bboxes:
                        f.write(','.join([str(i) for i in x])+'\n')
                result_path = os.path.join(video_path,
                        '{}_001_confidence.value'.format(video.name))
                with open(result_path, 'w') as f:
                    for x in scores:
                        f.write('\n') if x is None else f.write("{:.6f}\n".format(x))
                result_path = os.path.join(video_path,
                        '{}_time.txt'.format(video.name))
                with open(result_path, 'w') as f:
                    for x in track_times:
                        f.write("{:.6f}\n".format(x))
            elif 'GOT-10k' == args.dataset:
                video_path = os.path.join('results', args.dataset, model_name, video.name)
                if not os.path.isdir(video_path):
                    os.makedirs(video_path)
                result_path = os.path.join(video_path, '{}_001.txt'.format(video.name))
                with open(result_path, 'w') as f:
                    for x in pred_bboxes:
                        f.write(','.join([str(i) for i in x])+'\n')
                result_path = os.path.join(video_path,
                        '{}_time.txt'.format(video.name))
                with open(result_path, 'w') as f:
                    for x in track_times:
                        f.write("{:.6f}\n".format(x))
            else:
                model_path = os.path.join('results', args.dataset, model_name)
                if not os.path.isdir(model_path):
                    os.makedirs(model_path)
                result_path = os.path.join(model_path, '{}.txt'.format(video.name))
                with open(result_path, 'w') as f:
                    for x in pred_bboxes:
                        f.write(','.join([str(i) for i in x])+'\n')
            print('({:3d}) Video: {:12s} Time: {:5.1f}s Speed: {:3.1f}fps'.format(
                v_idx+1, video.name, toc, idx / toc))
    
    print("time cost:", model.time_cost / model.count)
    
if __name__ == '__main__':
    main()
