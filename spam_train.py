# coding:utf-8
from NB_train import NB_train

nb = NB_train()
file = 'spam.csv'
l, r = 0, 0
with open(file, 'r',encoding="UTF-8") as csv_file:
    lines = csv_file.read().split('\"\n\"')
for line in lines:
    l+=1
    rows = line.split('\",\"')
    for row in rows:
        r+=1
        name = "{0}:{1}:{2}".format(file,l,r)
        nb.train(sentence = row, category = "spam", name = name)
        print("{0} done.".format(name))
nb.done()
