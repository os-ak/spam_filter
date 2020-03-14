#!/usr/bin/env python
# -*- coding: utf-8 -*-

import numpy as np
import MySQLdb
import gc
import MeCab
from sklearn.naive_bayes import MultinomialNB
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from sklearn.metrics import classification_report
from sklearn.feature_extraction.text import TfidfTransformer
from sklearn.model_selection import cross_val_score
from sklearn.model_selection import KFold

DB_HOST='sp2017.cf'#ホスト名
DB_USER='user1'#ユーザ名
DB_PAWD='pass'#パスワード
DB='sp2017'#データベース名
connection = MySQLdb.connect(host=DB_HOST, user=DB_USER, passwd=DB_PAWD, db=DB, charset='utf8')
cursor = connection.cursor()
label_cat = {"ham":0, "spam":1}
label_value = {0:"ham", 1:"spam"}

def to_words(sentence):
    tagger = MeCab.Tagger('mecabrc')  # 別のTaggerを使ってもいい
    mecab_result = tagger.parse(sentence)
    info_of_words = mecab_result.split('\n')
    words = []
    for info in info_of_words:
        # macabで分けると、文の最後に’’が、その手前に'EOS'が来る
        if info == 'EOS' or info == '':
            break
            # info => 'な\t助詞,終助詞,*,*,*,*,な,ナ,ナ'
        info_elems = info.split(',')
        try:
            part = info_elems[0].split('\t')[1]#品詞を取り出す
        except:
            continue
        name = info_elems[2]
        num = info_elems[1]
        if part != '助詞' and part != '助動詞' and part != '接続詞' and part != '記号' and num != '数' and name != '人名':
            # 6番目に、無活用系の単語が入る。もし6番目が'*'だったら0番目を入れる
            if info_elems[6] == '*':
                # info_elems[0] => 'ヴァンロッサム\t名詞'
                words.append(info_elems[0][:-3])
                continue
            words.append(info_elems[6])
    return tuple(words)

def extraction_from_file(limit):
    counts = np.load("/tmp/sp2017/common/counts.npy")[:,:limit]
    #counts = np.load("counts.npy")[:,:limit]
    #ラベルを生成
    cursor.execute("SELECT category from doc_table order by doc_id")
    cat = cursor.fetchall()

    label = np.array([label_cat[c[0]] for c in cat])

    return counts[:, 1:], label

def extraction_to_file():
    #相互情報量の平均でソートし降順で単語を得る pmi>0.00115以上
    cursor.execute("SELECT word, avg(pmi) from word_dict_table where state = True and pmi > 0.00115 group by word order by avg(pmi) desc")
    top_words = cursor.fetchall()
    cursor.execute("SELECT doc_id from doc_table order by doc_id")
    num_of_docs = cursor.fetchall()
    counts = np.c_[np.zeros(len(num_of_docs))]
    l = 0
    for w in top_words:
        #各メールにおける単語wの出現回数を検索　doc_idの昇順で得る
        cursor.execute("""SELECT COALESCE(dw.times,0) as times from doc_table as dt
                    left outer join (select doc_id, times from doc_word_table where word = %s) as dw
                    on dw.doc_id = dt.doc_id order by dt.doc_id""",(w[0],))
        doc = cursor.fetchall()
        l += 1
        if l % 100 == 0 : print("{} done.".format(l))
        #print(l)
        docs_counts_by_word  = np.c_[[d[0] for d in doc]]
        counts = np.hstack([counts,docs_counts_by_word])
    np.save("counts.npy",counts)

def doc_to_count(top_words, doc):
    #テストデータの構文解析および単語数のカウント
    counts = []
    words = to_words(doc)
    for w in top_words:
        counts.append(words.count(w[0]))
    X_test = np.array(counts)
    return X_test

def calc_tfidf(X_train, X_test):
    #学習データとテストデータを結合
    counts = np.vstack((X_train,X_test))
    #tfidfの計算
    transformer = TfidfTransformer(smooth_idf=True)
    tfidf = transformer.fit_transform(counts)
    del counts
    #tfidfを学習データをテストデータに再び分割
    num_train = len(X_train)
    train = tfidf.toarray()[:num_train,:]
    test =  tfidf.toarray()[num_train:,:]
    del tfidf
    return train, test

def classify_proba(X_train, X_test, y_train, tfidf = True):
    if tfidf: X_train, X_test = calc_tfidf(X_train, X_test)
    #ナイーブベイズ
    nb_clf = MultinomialNB()
    nb_clf.fit(X_train, y_train.ravel()) # 学習をする
    return nb_clf.predict_proba(X_test)

def Kfold_measuremnt():
    counts, label = extraction_from_file(5000)
    transformer = TfidfTransformer(smooth_idf=True)
    tfidf = transformer.fit_transform(counts)
    kfold = KFold(n_splits=10, random_state=42)
    return cross_val_score(MultinomialNB(), tfidf, y=label, cv = kfold, scoring = "accuracy")

def classify_from_doc(doc, limit):
    cursor.execute("SELECT word, avg(pmi) from word_dict_table where state = True group by word order by avg(pmi) desc limit 0, %s",(limit,))
    top_words = cursor.fetchall()
    X_test = doc_to_count(top_words, doc)
    X_train, y_train = extraction_from_file(limit+1)
    result = classify_proba(X_train = X_train, X_test = X_test, y_train = y_train, tfidf = True)
    return result[0]

if __name__ == '__main__':
    #extraction_to_file()
    print(Kfold_measuremnt().mean())
    #DBへの操作を確定
    connection.commit()
    #MySQL接続を終了
    connection.close()
