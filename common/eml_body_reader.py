#!/usr/bin/env python
# -*- coding: utf-8 -*-
import email
import re

def parse(email_message, mode = 0, sj = False, ret_att = False):
    if mode == 0:#ドメインもヘッダも削除
        hd = re.compile(r"<[^>]*?>|(http|https|ftp)://((([1-9]?[0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}(1[0-9]{2}|2[0-4][0-9]|25[0-5]|[1-9]?[0-9])|(([A-Za-z0-9]\.|[A-Za-z0-9][A-Za-z0-9\-]{0,61}[A-Za-z0-9]\.)+[A-Za-z]+)[/\S]*)")
    elif mode == 1: #ヘッダのみ削除
        hd = re.compile(r"<[^>]*?>")
    elif mode == 2: #本文をそのまま返す
        hd = re.compile(r"")
    body = ''
    boundary = ''
    content_type = ["",""]
    for part in email_message.walk():
        if part.get_content_maintype() == 'multipart':
            content_type[0] = 'multipart'
            content_type[1] = part.get_content_subtype()
            boundary = part.get_boundary()
            continue
        if content_type[0] == '':
            content_type[0] = part.get_content_maintype()
            content_type[1] = part.get_content_subtype()
        else:
            content_type.append(part.get_content_subtype())
        attach_fname = part.get_filename()
        if not attach_fname:
            charset = str(part.get_content_charset())
            if sj == True:
                body += hd.sub('',part.get_payload(decode=True).decode("shift_jis", errors="replace"))
                continue
            if charset != "None":
                #print("Charset : {}".format(charset))
                body += hd.sub('',part.get_payload(decode=True).decode(charset, errors="replace"))
            else:
                data, encode = conv_encoding(part.get_payload(decode = True))
                if not encode:
                    print("Encode ERROR")
                    continue #どれでもエンコード出来ない場合は無視
                print("Encode : {}".format(encode))
                body += hd.sub('', data)
    if ret_att: return body, attach_fname #添付ファイル名も一緒に返す
    else: return body, content_type, boundary

def conv_encoding(part):
        lookup = ('iso-2022-jp','shift_jis','utf_8' ,'euc_jp', 'ascii')
        encode = None
        data = None
        for encoding in lookup:
            try:
                data = part.decode(encoding)
                encode = encoding
                break
            except:
                pass
        return data, encode

if __name__ == '__main__':
    while(True):
        eml = input(">>")
        with open(eml, 'rb') as email_file:
            email_message = email.message_from_bytes(email_file.read())
        print(parse(email_message=email_message))
