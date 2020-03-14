import paramiko
import datetime
import locale
import MySQLdb
import email
from eml_parser import parse
import re
DB_HOST='sp2017.cf'#ホスト名
DB_USER='user1'#ユーザ名
DB_PAWD='pass'#パスワード
DB='sp2017'#データベース名
SSH_HOST = 'mail-log.net.cs.tuat.ac.jp'
SSH_USER = ''#ユーザ名
SSH_PORT = 22001
SSH_PSWD = ''#パスワード
PRIVATE_KEY = 'id_rsa'#秘密鍵の場所
cursor = None
dt = datetime.datetime.today()
uptime = dt.strftime("%Y-%m-%d")

def main():
    global cursor
    #MySQLに接続
    connection = MySQLdb.connect(host=DB_HOST, user=DB_USER, passwd=DB_PAWD, db=DB, charset='utf8')
    cursor = connection.cursor()

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    #SSH接続開始
    ssh.connect(SSH_HOST, SSH_PORT, username=SSH_USER, password=SSH_PSWD, key_filename=PRIVATE_KEY)
    sftp = ssh.open_sftp()

    #ipアドレスを登録
    if 0:#登録する場合はここを1にする
        for i in range(1000):
            i = str(i)
            ssh.exec_command(r"""grep -E -r -o 'Received: from [a-zA-Z0-9\.\(\) -]+(\[|\()(([1-9]?[0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}(1[0-9]{2}|2[0-4][0-9]|25[0-5]|[1-9]?[0-9])' /var/spam/"""+i+r""" > text1.txt;
            grep -E -o '[a-zA-Z0-9\/]+.eml:' text1.txt > text3.txt;
            grep -E -o '(\[|\()(([1-9]?[0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}(1[0-9]{2}|2[0-4][0-9]|25[0-5]|[1-9]?[0-9])$' text1.txt | sed -E 's/(\(|\[)//g' > text2.txt""")
            stdin, stdout, stderr = ssh.exec_command(r"paste -d '\0' text3.txt text2.txt | sort -t, | uniq | sed 's/:/,/g' ")
            ips = stdout.read().decode('utf-8','ignore').split('\n')
            for ip in ips:
                d = ip.split(",")
                if len(d) != 2:
                    continue
                record_ip(d[1])
            print('No.'+i+' ip entry complete')

    #domainを登録
    if 0:#登録する場合はここを1にする
        for i in range(1000):
            i = str(i)
            stdin, stdout, stderr = ssh.exec_command("""grep -r -E -o '(http|https|ftp)://((([1-9]?[0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}(1[0-9]{2}|2[0-4][0-9]|25[0-5]|[1-9]?[0-9])|(([A-Za-z0-9]\.|[A-Za-z0-9][A-Za-z0-9\-]{0,61}[A-Za-z0-9]\.)+[A-Za-z]+))' /var/spam/"""+i+""" | sed -E "s/(http|https|ftp):\/\///g" | uniq | sort -t, | sed "s/:/,/g" """)
            dms = stdout.read().decode('utf-8','ignore').split('\n')

            for dm in dms:
                d = dm.split(",")
                if len(d) != 2:
                    continue
                record_domain(d[1])
            print('No.'+i+' domain entry complete')
    #本文がASCIIでエンコードされているメールのdomain登録
    if 1:
        p = re.compile(r"(http|https|ftp)://((([1-9]?[0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}(1[0-9]{2}|2[0-4][0-9]|25[0-5]|[1-9]?[0-9])|(([A-Za-z0-9]\.|[A-Za-z0-9][A-Za-z0-9\-]{0,61}[A-Za-z0-9]\.)+[A-Za-z]+))")
        for i in range(1000):
            i = str(i)
            #http/httpから始まるドメインがないファイルを抽出
            stdin, stdout, stderr = ssh.exec_command("""grep  -L -r -E -o '(http|https|ftp)://((([1-9]?[0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}(1[0-9]{2}|2[0-4][0-9]|25[0-5]|[1-9]?[0-9])|(([A-Za-z0-9]\.|[A-Za-z0-9][A-Za-z0-9\-]{0,61}[A-Za-z0-9]\.)+[A-Za-z]+))' /var/spam/"""+i)
            dms = stdout.read().decode('utf-8','ignore').split('\n')
            for dm in dms:
                if dm == "": break
                spamf = sftp.open(dm,'r')
                email_message = email.message_from_bytes(spamf.read())
                spamf.close
                try:
                    body = parse(email_message, d = False)
                except:
                    print("error path : {0}".format(dm))
                    continue
                ds = p.finditer(body)
                domains = []
                for d in ds:
                    url = d.group()
                    domains.append(re.sub(r"(http|https|ftp)://","",url))
                domains = set(domains)#重複ドメイン削除
                for d in domains:
                    record_domain(d)
            connection.commit()
            print('No.'+i+' domain entry complete')

    #DBへの操作を確定
    connection.commit()
    #MySQL接続を終了
    connection.close()
    #SFTP接続終了
    sftp.close()
    #SSH接続終了
    ssh.close()

def record_domain(ui):
    global cursor, d
    try:
        cursor.execute("SELECT domain FROM domain_table WHERE domain=%s", (ui,))
        result = cursor.fetchone()

        if result != None:
            #domain_tableのtimesを+1、update_dateに現在の日付
            cursor.execute("update domain_table set times=times+1,update_date=%s where domain=%s",(uptime,ui))
        else:
            cursor.execute("insert into domain_table values(%s,'1',-1,%s,null)",(ui,uptime))
    except MySQLdb.Error as e:
        print("ERROR")

def record_ip(ip):
    global cursor, d
    try:
        cursor.execute("SELECT ip FROM ip_table WHERE ip=%s", (ip,))
        result = cursor.fetchone()

        if result != None:
            #ip_tableのtimesを+1、update_dateに現在の日付
            cursor.execute("update ip_table set times=times+1,update_date=%s where ip=%s",(uptime,ip))
        else:
            cursor.execute("insert into ip_table values(%s,'1',%s)",(ip,uptime))
    except MySQLdb.Error as e:
           print("ERROR")

def record_union(ui, ip):
    global cursor
    try:
        #unionに現在調べているuiとipの組み合わせがあったら更新、なければ新規登録
        cursor.execute("SELECT domain,ip FROM union_table WHERE domain=%s AND ip=%s", (ui,ip))
        result = cursor.fetchone()
        if result != None:
            cursor.execute("update union_table set times=times+1,update_date=%s where domain=%s AND ip=%s", (uptime,ui,ip))
        else:
           cursor.execute("insert into union_table values(%s,%s,'1',%s)",(ui,ip,uptime))
    except MySQLdb.Error as e:
           print("ERROR")

if __name__ == '__main__':
    main()
