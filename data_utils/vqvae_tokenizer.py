# -*- encoding: utf-8 -*-
'''
@File    :   vqvae_tokenizer.py
@Time    :   2021/01/11 17:57:43
@Author  :   Ming Ding 
@Contact :   dm18@mails.tsinghua.edu.cn
'''

# here put the import lib
import os
import sys
import math
import random
from tqdm import tqdm

import numpy as np
import torch
import torch.nn.functional as F
import torch_xla.core.xla_model as xm

from vqvae import new_model, img2code, code2img
from torchvision import transforms
from PIL import Image

def is_exp2(x):
    t = math.log2(x)
    return abs(t - int(t)) < 1e-4
def sqrt_int(x):
    r = int(math.sqrt(x) + 1e-4)
    assert r * r == x
    return r

class VQVAETokenizer(object):
    def __init__(self, 
            model_path, 
            device = 'cpu'
        ):
#         print(model_path)
#         print(torch.load(model_path, map_location="cpu"))
        ckpt = torch.load(model_path, map_location="cpu")
    
        model = new_model()

        if list(ckpt.keys())[0].startswith('module.'):
            ckpt = {k[7:]: v for k, v in ckpt.items()}

        model.load_state_dict(ckpt)
        
        device = xm.xla_device()
        model = model.to(device)
        model.eval()

        self.model = model
        self.device = device
        self.image_tokens = model.quantize_t.n_embed
        self.num_tokens = model.quantize_t.n_embed

    def __len__(self):
        return self.num_tokens

    def EncodeAsIds(self, img):
        assert len(img.shape) == 4 # [b, c, h, w]
        return img2code(self.model, img)

    def DecodeIds(self, code, shape=None):
        if shape is None:
            if isinstance(code, list):
                code = torch.tensor(code, device=self.device)
            s = sqrt_int(len(code.view(-1)))
            assert s * s == len(code.view(-1))
            shape = (1, s, s)
        code = code.view(shape)
        out = code2img(self.model, code)
        return out

    def read_img(self, path, img_size=256):
        tr = transforms.Compose([
            transforms.Resize(img_size), 
            transforms.CenterCrop(img_size),
            transforms.ToTensor(),
        ])
        img = tr(Image.open(path))
        if img.shape[0] == 4:
            img = img[:-1]
        tr_normalize = transforms.Normalize([0.79093, 0.76271, 0.75340], [0.30379, 0.32279, 0.32800])
        img = tr_normalize(img)
        img = img.unsqueeze(0).float().to(self.device) # size [1, 3, h, w]
        return img  
