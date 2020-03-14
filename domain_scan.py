import requests
import urllib
import json
import MySQLdb
import time
import datetime
DB_HOST="sp2017.cf"#ホスト名
DB_USER='user1'#ユーザ名
DB_PAWD='pass'#パスワード
DB='sp2017'#データベース名
N = 0
connection = MySQLdb.connect(host=DB_HOST, user=DB_USER, passwd=DB_PAWD, db=DB, charset='utf8')
cursor = connection.cursor()

def analysis_detection(json_response):
    for i in range(0,len(json_response)):
        domain = json_response[i]['resource']
        if json_response[i]['response_code'] == 0:#VTに情報がない場合
            insert_detection(domain, -1)
        else:
            pos_vacccines=[]
            stat = json_response[i]['positives']
            if stat > 0:#脅威がある
                vaccines = list(json_response[i]['scans'].keys())#ワクチンサイト名を取得
                for v in vaccines:
                    if json_response[i]['scans'][v]['detected'] == True:
                        pos_vacccines.append(v)
                insert_detection(domain, stat, pos_vacccines)
            elif stat == 0:#脅威なし
                insert_detection(domain, 0)

def insert_detection(domain, stat, vaccines=None):
    global N
    d = datetime.datetime.today()
    uptime = d.strftime("%Y-%m-%d")
    cursor.execute("update domain_table set state=%s,detection_date=%s where domain=%s",(stat,uptime,domain))
    N -= 1
    if stat>=1:
        for vaccine in vaccines:
            cursor.execute("SELECT domain,vaccine FROM detection_table WHERE domain=%s AND vaccine=%s", (domain,vaccine))
            if cursor.fetchone() != None: #日付更新
                cursor.execute("update detection_table set update_date=%s WHERE domain=%s AND vaccine=%s",(uptime,domain,vaccine))
            else: #新規登録
                cursor.execute("insert into detection_table values(%s,%s,%s)",(domain,vaccine,uptime))
    print('{0} items remaining'.format(N))
    if stat>=1:
        print('threat found. domain:{0} state:{1} vaccines:{2}'.format(domain,stat,vaccines))
    #DBへの操作を確定
    connection.commit()

def main():
    global N
    cursor.execute("SELECT domain FROM domain_table WHERE detection_date is NULL")
    domains = cursor.fetchall()
    N = len(domains)
    dms = [domains[i:i+4] for i in range(0,len(domains),4)] #4分割
    for dm in dms:
        headers = {
        "Accept-Encoding": "gzip, deflate",
        "User-Agent" : "gzip,  My Python requests library example client or username"
        }
        parm = ''
        for d in dm:
            parm += d[0]+'\n'
        params = {'apikey': '8807e3024e59bd4c4d9c2b57f6c78e334d4fd2dc290a3257e59dfc8a2e4a50e8', 'resource':parm}
        response = requests.post('https://www.virustotal.com/vtapi/v2/url/report', params=params, headers=headers)
        start = time.time()
        try:
            analysis_detection(response.json())
        except:
            print("Limit exceeded")
            break;
        psed_time = time.time() - start
        time.sleep(15-psed_time)

    #MySQL接続を終了
    connection.close()

if __name__ == '__main__':
    main()
