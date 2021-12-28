# -*- coding: utf-8 -*-

import numpy as np

class TextlineMergeConfig(object):
    def __init__(self):
        self.gamma = 0.5
        self.sigma = 2
        self.std_threshold = 11.0

class OCRConfig(object):
    def __init__(self):
        self.prob_threshold = 0.4
        self.max_chunk_size = 16
        
class TextRendererConfig(object):
    def __init__(self):
        self.word_gap = 10  