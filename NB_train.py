import math
import sys
import MeCab
import MySQLdb
import warnings
DB_HOST='sp2017.cf'#ホスト名
DB_USER='user1'#ユーザ名
DB_PAWD='pass'#パスワード
DB='sp2017'#データベース名
#DBリセット手順
# doc_word_table -> word_dict_table -> doc_table -> category_table
class NB_train():
    def __init__(self):
        warnings.filterwarnings('ignore')
        self.connection = MySQLdb.connect(host=DB_HOST, user=DB_USER, passwd=DB_PAWD, db=DB, charset='utf8')
        self.cursor = self.connection.cursor()

    def train(self, sentence, category, name = None):
        doc_id = self.entry_category(category,name)
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
            # 6番目に、無活用系の単語が入る。もし6番目が'*'だったら0番目を入れる
            try:
                part = info_elems[0].split('\t')[1]#品詞を取り出す
            except:
                print(info)
                continue
            if part != '助詞' and part != '助動詞' and part != '接続詞' and part != '記号' and info_elems[1] != '数' and info_elems[2] != '人名':
                if info_elems[6] == '*':
                    # info_elems[0] => 'ヴァンロッサム\t名詞'
                    word = info_elems[0][:-3]
                else:
                    word = info_elems[6]
                self.entry_word(word, category, doc_id)
    def entry_category(self, category, name):
        #カテゴリーがなければ追加
        self.cursor.execute("INSERT IGNORE INTO category_table values(%s)",(category,))
        #ドキュメント情報を1つ追加
        if name is not None:
            self.cursor.execute("INSERT INTO doc_table(category,name) values(%s,%s)",(category,name))
        else:
            self.cursor.execute("INSERT INTO doc_table(category) values(%s)",(category,))
        #割り当てられたdoc_idを取得
        self.cursor.execute("SELECT auto_increment FROM information_schema.tables WHERE table_name = 'doc_table'")
        doc_id = self.cursor.fetchone()[0] - 1
        return doc_id

    def entry_word(self, word, category, doc_id):
        #単語がなければ追加
        self.cursor.execute("INSERT IGNORE INTO word_dict_table(word,category,state,pmi) values(%s,%s,true,0)",(word,category))
        #ドキュメント内に単語が登録されているか
        self.cursor.execute("SELECT * FROM doc_word_table WHERE word=%s AND doc_id=%s", (word,doc_id))
        result = self.cursor.fetchone()
        if result != None:
            #あれば更新
            self.cursor.execute("UPDATE doc_word_table SET times=times+1 WHERE word=%s AND doc_id=%s", (word,doc_id))
        else:
            #なければ追加
            self.cursor.execute("INSERT INTO doc_word_table(doc_id,word,times) values(%s,%s,1)",(doc_id,word))

    #カテゴリtargetにおける相互情報量を計算するメソッド
    def pmi(self, target):
        self.cursor.execute("""SELECT count(distinct doc_id) FROM doc_table where category=%s""",(target,))
        Np = self.cursor.fetchone()[0]
        # wordを含むtarget以外の文書数
        self.cursor.execute("""SELECT count(distinct doc_id) FROM doc_table where category!=%s""",(target,))
        Nn = self.cursor.fetchone()[0]
        #総文書数
        N = Np + Nn

        #全てのユニークな単語に対して
        self.cursor.execute("""SELECT distinct word FROM word_dict_table where state = true and category = %s""",(target,))
        words = self.cursor.fetchall()
        for word in words:
            word = word[0]
            # N11とN10をカウント
            #wordを含むtargetの文書数
            self.cursor.execute("""SELECT count(distinct dt.doc_id) FROM doc_word_table as dw, doc_table as dt where dw.doc_id = dt.doc_id AND category = %s AND word = %s""",(target,word))
            n11 = self.cursor.fetchone()[0]
            #wordを含まないtargetの文書数
            self.cursor.execute("""SELECT count(distinct dt.doc_id) FROM doc_word_table as dw, doc_table as dt where dw.doc_id = dt.doc_id AND category != %s AND word = %s""",(target,word))
            n10 = self.cursor.fetchone()[0]
            n01 = Np - n11
            n00 = Nn - n10
            try:
                # 相互情報量の定義の各項を計算
                #出現頻度が0.0になってしまうものに対してはスムージング(+1)をしている
                temp1 = n11/N * math.log((N*(n11+1))/((n10+n11)*(n01+n11)), 2)
                temp2 = n01/N * math.log((N*(n01+1))/((n00+n01)*(n01+n11)), 2)
                temp3 = n10/N * math.log((N*(n10+1))/((n10+n11)*(n00+n10)), 2)
                temp4 = n00/N * math.log((N*(n00+1))/((n00+n01)*(n00+n10)), 2)
                score = temp1 + temp2 + temp3 + temp4
            except:
                #0で割る者は強制的に0
                score = 0.0
            self.cursor.execute(""" UPDATE word_dict_table set pmi = %s where word = %s AND category = %s""",(str(score),word,target))


    #学習終了時に呼ばれる pmiを計算し更新する
    def done(self):
        self.cursor.execute("""SELECT category FROM category_table""")
        categories = self.cursor.fetchall()
        for category in categories:
            self.pmi(target = category)
        self.connection.commit()
        self.connection.close()

if __name__ == '__main__':

    nb = NB_train()

    nb.train('''Python（パイソン）は，オランダ人のグイド・ヴァンロッサムが作ったオープンソースのプログラミング言語。
                オブジェクト指向スクリプト言語の一種であり，Perlとともに欧米で広く普及している。イギリスのテレビ局 BBC が製作したコメディ番組『空飛ぶモンティパイソン』にちなんで名付けられた。
                Python は英語で爬虫類のニシキヘビの意味で，Python言語のマスコットやアイコンとして使われることがある。Pythonは汎用の高水準言語である。プログラマの生産性とコードの信頼性を重視して設計されており，核となるシンタックスおよびセマンティクスは必要最小限に抑えられている反面，利便性の高い大規模な標準ライブラリを備えている。
                Unicode による文字列操作をサポートしており，日本語処理も標準で可能である。多くのプラットフォームをサポートしており（動作するプラットフォーム），また，豊富なドキュメント，豊富なライブラリがあることから，産業界でも利用が増えつつある。
             ''',
             'Python')
    nb.train('''ヘビ（蛇）は、爬虫綱有鱗目ヘビ亜目（Serpentes）に分類される爬虫類の総称。
                体が細長く、四肢がないのが特徴。ただし、同様の形の動物は他群にも存在する。
                ''', 'Snake')
    nb.train('''Ruby（ルビー）は，まつもとゆきひろ（通称Matz）により開発されたオブジェクト指向スクリプト言語であり，
                従来 Perlなどのスクリプト言語が用いられてきた領域でのオブジェクト指向プログラミングを実現する。
                Rubyは当初1993年2月24日に生まれ， 1995年12月にfj上で発表された。
                名称のRubyは，プログラミング言語Perlが6月の誕生石であるPearl（真珠）と同じ発音をすることから，
                まつもとの同僚の誕生石（7月）のルビーを取って名付けられた。
             ''',
             'Ruby')
    nb.train('''ルビー（英: Ruby、紅玉）は、コランダム（鋼玉）の変種である。赤色が特徴的な宝石である。
                天然ルビーは産地がアジアに偏っていて欧米では採れないうえに、
                産地においても宝石にできる美しい石が採れる場所は極めて限定されており、
                3カラットを超える大きな石は産出量も少ない。
             ''', 'Gem')
    nb.done()
