#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import email
import lxml.html
import base64
import quopri
import re
import MySQLdb
from eml_body_reader import parse
from sklearn_NB import classify_from_doc
from email.message import Message
from email.header import decode_header
from email.header import Header
from email import generator

class Risk_Judge(object):
    def __init__(self, mail_file_path, current_time):
        DB_HOST='sp2017.cf'#ホスト名
        DB_USER='user1'#ユーザ名
        DB_PAWD='pass'#パスワード
        DB='sp2017'#データベース名
        connection = MySQLdb.connect(host=DB_HOST, user=DB_USER, passwd=DB_PAWD, db=DB, charset='utf8')
        self.mail_file_path = mail_file_path
        self.current_time = current_time
        self.cursor = connection.cursor()
        self.domain_results = []
        self.ip_results = []
        self.body_score = []
        self.attach_fname = None
        self.content_type = []
        self.boundary = ''
        self.total_score = 0
        self.subject_label = ''
        self.mail_plain_data = None

        # emlファイルをバイナリで開きemail.message.Messageインスタンスの取得
        with open(self.mail_file_path, 'rb') as email_file:
            self.email_message = email.message_from_bytes(email_file.read())
        self.body_no_doamin, self.attach_fname = parse(email_message = self.email_message, mode = 0, ret_att = True)
        self.body_with_domain, self.content_type, self.boundary = parse(email_message = self.email_message, mode = 2, ret_att = False)
        #emlファイルをそのまま開く
        with open(self.mail_file_path, 'r',encoding="UTF-8") as email_file:
            self.mail_plain_data = email_file.read()
            self.ip_check(self.mail_plain_data)#ipアドレス検査
        self.domain_check()#ドメイン検査
        self.body_check()#本文分類
        connection.commit()
        connection.close()
        self.calc_score()
        self.edit()#メールファイル書き換え
    def calc_score(self):
        #label = {0:"Safe", 1:"Low", 2:"Medium", 3:"High", 4:"Critical"}
        #label = {0:"安全", 1:"", 2:"不審", 3:"注意", 4:"危険"}
        label = {0:"危険度0", 1:"危険度1", 2:"危険度2", 3:"危険度3", 4:"危険度4"}
        for domain_result in self.domain_results:
            if(int(domain_result[2]) > 0): self.total_score+=6
            if(int(domain_result[1]) >= 50): self.total_score+=5
            elif(int(domain_result[1]) > 0): self.total_score+=4
        for ip_result in self.ip_results:
            if(int(ip_result[1]) > 0): self.total_score+=1
        if(self.body_score[1] >= 95): self.total_score+=4
        elif(self.body_score[1] >= 80): self.total_score+=2
        elif(self.body_score[1] >= 50): self.total_score+=1
        if(self.total_score >= 10): self.subject_label = label[4]
        elif(self.total_score >= 5): self.subject_label = label[3]
        elif(self.total_score >= 2): self.subject_label = label[2]
        elif(self.total_score >= 1): self.subject_label = label[1]
        elif(self.total_score >= 0): self.subject_label = label[0]

    def ip_check(self, body_source):
        re_ip1 = re.compile(r'Received: from [a-zA-Z0-9\.\(\) -]*(\[|\()(([1-9]?[0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}(1[0-9]{2}|2[0-4][0-9]|25[0-5]|[1-9]?[0-9])')
        re_ip2 = re.compile(r'(([1-9]?[0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}(1[0-9]{2}|2[0-4][0-9]|25[0-5]|[1-9]?[0-9])')
        receives = re_ip1.finditer(body_source)
        ips = []
        for r in receives:
            line = re_ip2.finditer(r.group())
            for l in line:
                ips.append(l.group())
        ips = set(ips)#重複ドメイン削除
        for ip in ips:
            self.cursor.execute("SELECT times from ip_table where ip = %s",(ip,))
            result = self.cursor.fetchone()
            if result is None: self.ip_results.append([ip,"0"])
            else: self.ip_results.append([ip,result[0]])

    def domain_check(self):
        re_domain = re.compile(r"(http|https|ftp)://((([1-9]?[0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}(1[0-9]{2}|2[0-4][0-9]|25[0-5]|[1-9]?[0-9])|(([A-Za-z0-9]\.|[A-Za-z0-9][A-Za-z0-9\-]{0,61}[A-Za-z0-9]\.)+[A-Za-z]+))")
        ds = re_domain.finditer(self.body_with_domain)
        domains = []
        for d in ds:
            domains.append(re.sub(r"(http|https|ftp)://","", d.group()))
        domains = set(domains)#重複ドメイン削除
        for domain in domains:
            self.cursor.execute("SELECT times, state from domain_table where domain = %s",(domain,))
            result = self.cursor.fetchone()
            if result is None: self.domain_results.append([domain,"0","-1"])
            else: self.domain_results.append([domain,result[0],result[1]])

    def body_check(self):
        self.body_score = classify_from_doc(self.body_no_doamin, 4200)
        self.body_score[0]*=100
        self.body_score[1]*=100

    def edit(self):
        subject, encoding = self._get_decoded_header("Subject")
        if not encoding: encoding = "UTF-8"
        rev_subject = "[{0}]{1}".format(self.subject_label, subject)#タイトル部分には点数のみ
        self.email_message.replace_header('Subject', Header(rev_subject,encoding).encode())#タイトル書き換え
        if self.content_type[0] == 'multipart':
            rev_text_body = """
-----------------------------------------------
Domain match {1}
IP address match {2}
Naive baise [ham:{3[0]:.2f}%, spam:{3[1]:.2f}%]
Total score {4}
Judgement date {5}
-----------------------------------------------
""".format(self.body_with_domain,self.domain_results,self.ip_results,self.body_score,self.total_score,self.current_time)
            #if self.content_type[1] == 'alternative':
            rev_html_body = """<p>
-----------------------------------------------------<br>
Domain match {1}<br>
IP address match {2}<br>
Naive baise [ham:{3[0]:.2f}%, spam:{3[1]:.2f}%]<br>
Total score {4}<br>
Judgement date {5}<br>
-----------------------------------------------------<br>
</p>""".format(self.body_with_domain,self.domain_results,self.ip_results,self.body_score,self.total_score,self.current_time)
            if "Content-Transfer-Encoding: base64" in self.mail_plain_data:
                html_body = base64.b64encode(rev_html_body.encode('utf-8')).decode(encoding='utf-8')
                text_body = base64.b64encode(rev_text_body.encode('utf-8')).decode(encoding='utf-8')
            else:
                html_body = rev_html_body
                text_body = rev_text_body
            with open(self.mail_file_path, 'r+') as eml:
                gen = generator.Generator(eml)
                gen.flatten(self.email_message)
                eml.seek(0)
                old_body = eml.read()
                body_list = old_body.split("--"+self.boundary)
                for i in range(1,len(self.content_type)-1):
                    if self.content_type[i+1]=="html":
                        body_list[i]+=(html_body+"\n")
                    else:
                        body_list[i]+=(text_body+"\n")
                rev_body = ("--"+self.boundary).join(body_list)
                eml.seek(0)
                eml.write(rev_body)
        else:
            if self.content_type[1] == "html":
                dom = lxml.html.fromstring(self.body_with_domain)
                body = dom.body
                new_tag = lxml.html.fromstring("""<p>
-----------------------------------------------------<br>
Domain match {1}<br>
IP address match {2}<br>
Naive baise [ham:{3[0]:.2f}%, spam:{3[1]:.2f}%]<br>
Total score {4}<br>
Judgement date {5}<br>
-----------------------------------------------------<br>
</p>""".format(self.body_with_domain,self.domain_results,self.ip_results,self.body_score,self.total_score,self.current_time))
                body.append(new_tag)
                rev_body = lxml.html.tostring(dom)
                self.email_message.replace_header('Content-Type',"text/html")
                self.email_message.set_payload(rev_body,"UTF-8")
            else:
                rev_body = """{0}
-----------------------------------------------
Domain match {1}
IP address match {2}
Naive baise [ham:{3[0]:.2f}%, spam:{3[1]:.2f}%]
Total score {4}
Judgement date {5}
-----------------------------------------------
""".format(self.body_with_domain,self.domain_results,self.ip_results,self.body_score,self.total_score,self.current_time)#ここに判定結果の詳細
                self.email_message.replace_header('Content-Type',"text/plain")
                self.email_message.set_payload(rev_body,"UTF-8")#強制的にUTF8に変換して本文書き換え <- 型によってはエンコード出来ない文字があるから
            with open(self.mail_file_path, 'w') as eml:
                gen = generator.Generator(eml)
                gen.flatten(self.email_message)

    def _get_decoded_header(self, key_name):
        ret = ""
        encoding = ""
        raw_obj = self.email_message.get(key_name)
        if raw_obj is None:
            return ""
        for fragment, encoding in decode_header(raw_obj):
            if not hasattr(fragment, "decode"):
                ret += fragment
                continue
            # encodeがなければとりあえずUTF-8でデコードする
            if encoding:
                ret += fragment.decode(encoding)
            else:
                ret += fragment.decode("UTF-8")
        return ret, encoding

if __name__ == "__main__":
    Risk_Judge(sys.argv[1],"0")
