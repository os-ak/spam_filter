#coding:utf-8
import codecs
import math
import sys
import MySQLdb
DB_HOST='sp2017.cf'#ホスト名
DB_USER='user1'#ユーザ名
DB_PAWD='pass'#パスワード
DB='sp2017'#データベース名
connection = MySQLdb.connect(host=DB_HOST, user=DB_USER, passwd=DB_PAWD, db=DB, charset='utf8')
cursor = connection.cursor()

#カテゴリtargetにおける相互情報量を計算する関数
def pmi(target):
    # wordを含むtargetの文書数
    cursor.execute("""SELECT count(distinct doc_id) FROM doc_table where category=%s""",(target,))
    Np = cursor.fetchone()[0]
    # wordを含むtarget以外の文書数
    cursor.execute("""SELECT count(distinct doc_id) FROM doc_table where category!=%s""",(target,))
    Nn = cursor.fetchone()[0]
    #総文書数
    N = Np + Nn

    #全てのユニークな単語に対して
    cursor.execute("""SELECT distinct word FROM word_dict_table where state = true and category = %s""",(target,))
    words = cursor.fetchall()
    for word in words:
        word = word[0]
        # N11とN10をカウント
        #wordを含むtargetの文書数
        cursor.execute("""SELECT count(distinct dt.doc_id) FROM doc_word_table as dw, doc_table as dt where dw.doc_id = dt.doc_id AND category = %s AND word = %s""",(target,word))
        n11 = cursor.fetchone()[0]
        #wordを含まないtargetの文書数
        cursor.execute("""SELECT count(distinct dt.doc_id) FROM doc_word_table as dw, doc_table as dt where dw.doc_id = dt.doc_id AND category != %s AND word = %s""",(target,word))
        n10 = cursor.fetchone()[0]
        n01 = Np - n11
        n00 = Nn - n10
        try:
            temp1 = n11/N * math.log((N*(n11+1))/((n10+n11)*(n01+n11)), 2)
            temp2 = n01/N * math.log((N*(n01+1))/((n00+n01)*(n01+n11)), 2)
            temp3 = n10/N * math.log((N*(n10+1))/((n10+n11)*(n00+n10)), 2)
            temp4 = n00/N * math.log((N*(n00+1))/((n00+n01)*(n00+n10)), 2)
            score = temp1 + temp2 + temp3 + temp4
        except:
            score = 0.0
        cursor.execute(""" UPDATE word_dict_table set pmi = %s where word = %s AND category = %s""",(str(score),word,target))


if __name__ == "__main__":
    cursor.execute("""SELECT category FROM category_table""")
    categories = cursor.fetchall()
    for category in categories:
        pmi(target = category)
    connection.commit()
    connection.close()
