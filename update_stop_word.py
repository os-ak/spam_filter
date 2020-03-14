import MySQLdb
DB_HOST='sp2017.cf'#ホスト名
DB_USER='user1'#ユーザ名
DB_PAWD='pass'#パスワード
DB='sp2017'#データベース名
connection = MySQLdb.connect(host=DB_HOST, user=DB_USER, passwd=DB_PAWD, db=DB, charset='utf8')
cursor = connection.cursor()

def write_stop_word():
    cursor.execute("SELECT word from word_dict_table where state = False")
    words = cursor.fetchall()
    with open("stop_words.dat","w",encoding="UTF-8") as f:
        for w in words:
            f.write(w[0]+"\n")

def read_stop_word():
    with open("stop_words.dat","r",encoding="UTF-8") as f:
        words = f.read().split("\n")
    for w in words:
        cursor.execute("UPDATE word_dict_table set state = False where word = %s",(w,))
    connection.commit()

if __name__ == '__main__':
    #write_stop_word()
    read_stop_word()
    connection.close()
