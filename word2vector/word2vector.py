# -*- coding:utf-8 -*-

import logging
from gensim.models.word2vec import LineSentence, Word2Vec
import sys
import os

target = os.path.join(dirname, '../dataset/target.txt')
trainedModel = os.path.join(dirname, '../model/w2v.mod')

dirname = os.path.dirname(__file__)
logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)

sentences= LineSentence(target)

model = Word2Vec(sentences ,min_count=1, iter=1000)
model.train(sentences, total_examples=model.corpus_count, epochs=1000)

model.save(trainedModel)