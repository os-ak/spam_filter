#!/usr/bin/env python
# -*- coding: utf-8 -*-
from datetime import datetime
from Risk_Judge import Risk_Judge
import shutil
import sys
import os
user_name = sys.argv[1]
current_time = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
log_file = open("/home/"+ user_name +"/Maildir/judge_log.txt","r+")
logs = log_file.read().split("\n")
path = "/home/"+ user_name +"/Maildir/new"
files = os.listdir(path)
for file in files:
    mail_file_path = "{0}/{1}".format(path,file)
    if mail_file_path in logs: continue
    work_path = "/home/"+ user_name +"/Maildir/work/"+file
    shutil.move(mail_file_path,work_path)
    Risk_Judge(work_path, current_time)
    shutil.move(work_path,mail_file_path)
    log_file.write(mail_file_path+"\n")
log_file.close()
