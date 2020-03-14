import os
import random
import paramiko
SSH_HOST = 'mail-log.net.cs.tuat.ac.jp'
SSH_USER = ''#ユーザ名
SSH_PORT = 22001
SSH_PSWD = ''#パスワード
PRIVATE_KEY = 'id_rsa'#秘密鍵の場所
max_iter = 4000#ランダムにダウンロードするファイル数
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
#SSH接続開始
ssh.connect(SSH_HOST, SSH_PORT, username=SSH_USER, password=SSH_PSWD, key_filename=PRIVATE_KEY)
sftp = ssh.open_sftp()
number = [(i,j) for i in range(0,394) for j in range(0,1000)]
l = random.choices(number,k=max_iter)
if not os.path.isdir('spam'):
    os.mkdir('spam')
for i in range(max_iter):
    spam_file = "/var/spam/{0}/{1:0>3}.eml".format(l[i][0],l[i][1])
    local_file = "./spam/spam{0:0>3}-{1:0>3}.eml".format(l[i][0],l[i][1])
    sftp.get(spam_file, local_file)
#SFTP接続終了
sftp.close()
#SSH接続終了
ssh.close()
