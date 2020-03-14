# coding:utf-8
import sys
import email
from eml_body_reader import parse
import os
import csv
import re
h = re.compile(r"spam*")
spams = []
path = "./spam"
files = os.listdir(path)
result = ""
for file in files:
    mail_file_path = "{0}/{1}".format(path,file)
    if not h.match(file): continue
    with open(mail_file_path, 'rb') as email_file:
        email_message = email.message_from_bytes(email_file.read())
        body = parse(email_message = email_message)
        result ="""
{0}
{1}
{2}
""".format(result,file,body)
        spams.append(body)

with open("spam.csv","w",encoding="UTF-8") as f:
    writer = csv.writer(f,lineterminator='\n')
    writer.writerow(spams)

#with open("result.txt","w",encoding="UTF-8") as f:
#    f.write(result)
