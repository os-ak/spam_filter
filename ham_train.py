# coding:utf-8
from NB_train import NB_train
import os

path = "./ham"
files = os.listdir(path)
nb = NB_train()
for file in files:
    l, r = 0, 0
    csv_file_path = "{0}/{1}".format(path,file)
    with open(csv_file_path, 'r', encoding="UTF-8") as csv_file:
        lines = csv_file.read().split('\"\n\"')
    for line in lines:
        l+=1
        rows = line.split('\",\"')
        for row in rows:
            r+=1
            name = "{0}:{1}:{2}".format(file,l,r)
            nb.train(sentence = row, category = "ham", name = name)
            print("{0} done.".format(name))
nb.done()
