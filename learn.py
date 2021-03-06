#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Trinkle23897"
__copyright__ = "Copyright (C) 2019 Trinkle23897"
__license__ = "MIT"
__email__ = "463003665@qq.com"

import os, sys, json, html, time, email, urllib, getpass, base64, argparse
from tqdm import tqdm
import urllib.request, http.cookiejar
from bs4 import BeautifulSoup as bs

url = 'http://learn.tsinghua.edu.cn'
user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36'
headers = {'User-Agent': user_agent, 'Connection': 'keep-alive'}
cookie = http.cookiejar.MozillaCookieJar()
handler = urllib.request.HTTPCookieProcessor(cookie)
opener = urllib.request.build_opener(handler)
urllib.request.install_opener(opener)

def open_page(uri, values={}):
    post_data = urllib.parse.urlencode(values).encode()
    request = urllib.request.Request(uri if uri.startswith('http') else url + uri, post_data, headers)
    try:
        response = opener.open(request)
        return response
    except urllib.error.URLError as e:
        print(e.code, ':', e.reason)

def get_page(uri, values={}):
    data = open_page(uri, values)
    if data:
        return data.read().decode()

def get_json(uri, values={}):
    return json.loads(get_page(uri, values))

def escape(s):
    return html.unescape(s).replace(os.path.sep, '、').replace(':', '_').replace(' ', '_').replace('\t', '').replace('?','.').replace('/','_').replace('\'','_').replace('<','').replace('>','').replace('#','').replace(';','').replace('*','_').replace("\"",'_').replace("\'",'_').replace('|','')

def login(username, password):
    login_uri = 'https://id.tsinghua.edu.cn/do/off/ui/auth/login/post/bb5df85216504820be7bba2b0ae1535b/0?/login.do'
    values = {'i_user': username, 'i_pass': password, 'atOnce': 'true'}
    info = get_page(login_uri, values)
    successful = 'SUCCESS' in info
    print('User %s login successfully' % (username) if successful else 'User %s login failed!' % (username))
    if successful:
        get_page(get_page(info.split('replace("')[-1].split('");\n')[0]).split('location="')[1].split('";\r\n')[0])
    return successful

def get_courses(args):
    try:
        if args.all or args.course or args.semester:
            query_list = [x for x in get_json('/b/wlxt/kc/v_wlkc_xs_xktjb_coassb/queryxnxq') if x != None]
            query_list.sort()
            if args.semester:
                query_list_ = [q for q in query_list if q in args.semester]
                if len(query_list_) == 0:
                    print('Invalid semester, choices: ', query_list)
                query_list = query_list_
        else:
            query_list = [get_json('/b/kc/zhjw_v_code_xnxq/getCurrentAndNextSemester')['result']['xnxq']]
    except:
        print('您被退学了！')
        return []
    courses = []
    for q in query_list:
        try:
            courses += get_json('/b/wlxt/kc/v_wlkc_xs_xktjb_coassb/pageList', {'aoData': [
                {"name": "xnxq", "value": q},
                {"name": "jslx", "value": "3"} # students
            ]})['object']['aaData']
            courses += get_json('/b/wlxt/kc/v_wlkc_xs_xktjb_coassb/pageList', {'aoData': [
                {"name": "xnxq", "value": q},
                {"name": "jslx", "value": "0"} # TA
            ]})['object']['aaData']
        except:
            continue
    escape_c = []
    for c in courses:
        c['kcm'] = escape(c['kcm']).replace(' ', '').replace('_', '').replace('（', '(').replace('）', ')')
        escape_c.append(c)
    courses = escape_c
    if args.course:
        courses = [c for c in courses if c['kcm'] in args.course]
    if args.ignore:
        courses = [c for c in courses if c['kcm'] not in args.ignore]
    return courses

class TqdmUpTo(tqdm):
    def update_to(self, b=1, bsize=1, tsize=None):
        if tsize is not None: self.total = tsize
        self.update(b * bsize - self.n)

def download(uri, name):
    filename = escape(name)
    if os.path.exists(filename) or 'Connection__close' in filename:
        return
    try:
        with TqdmUpTo(dynamic_ncols=True, unit='B', unit_scale=True, miniters=1, desc=filename) as t:
            urllib.request.urlretrieve(url+uri, filename=filename, reporthook=t.update_to, data=None)
    except:
        print('Could not download %s due to networking' % filename)
        return

def build_notify(s):
    tp = bs(base64.b64decode(s['ggnr']).decode('utf-8'), 'html.parser').text if s['ggnr'] else ''
    st = '题目: %s\n发布人: %s\n发布时间: %s\n内容: %s\n' % (s['bt'], s['fbr'], s['fbsjStr'], tp)
    return st

def sync_notify(c):
    pre = os.path.join(c['kcm'], '公告')
    if not os.path.exists(pre): os.makedirs(pre)
    try:
        data = {'aoData': [{"name": "wlkcid", "value": c['wlkcid']}]}
        if c['_type'] == 'student':
            notify = get_json('/b/wlxt/kcgg/wlkc_ggb/student/pageListXs', data)['object']['aaData']
        else:
            notify = get_json('/b/wlxt/kcgg/wlkc_ggb/teacher/pageList', data)['object']['aaData']
    except:
        return
    for n in notify:
        path = os.path.join(pre, escape(n['bt']) +'.txt')
        open(path, 'w', encoding='utf-8').write(build_notify(n))

def sync_file(c):
    now = os.getcwd()
    pre = os.path.join(c['kcm'], '课件')
    if not os.path.exists(pre): os.makedirs(pre)
    if c['_type'] == 'student':
        files = get_json('/b/wlxt/kj/wlkc_kjxxb/student/kjxxbByWlkcidAndSizeForStudent?wlkcid=%s&size=0' % c['wlkcid'])['object']
    else:
        files = get_json('/b/wlxt/kj/v_kjxxb_wjwjb/teacher/queryByWlkcid?wlkcid=%s&size=0' % c['wlkcid'])['object']['resultsList']
    for f in files:
        os.chdir(pre)
        name = f['bt']+'.'+f['wjlx'] if f['wjlx'] else f['bt']
        download('/b/wlxt/kj/wlkc_kjxxb/%s/downloadFile?sfgk=0&wjid=%s' % (c['_type'], f['wjid']), name=name)
        os.chdir(now)

def sync_info(c):
    pre = os.path.join(c['kcm'], '课程信息.txt')
    try:
        if c['_type'] == 'student':
            html = get_page('/f/wlxt/kc/v_kcxx_jskcxx/student/beforeXskcxx?wlkcid=%s&sfgk=-1' % c['wlkcid'])
        else:
            html = get_page('/f/wlxt/kc/v_kcxx_jskcxx/teacher/beforeJskcxx?wlkcid=%s&sfgk=-1' % c['wlkcid'])
        open(pre, 'w').write('\n'.join(bs(html, 'html.parser').find(class_='course-w').text.split()))
    except:
        return

def sync_hw(c):
    now = os.getcwd()
    pre = os.path.join(c['kcm'], '作业')
    if not os.path.exists(pre): os.makedirs(pre)
    data = {'aoData': [{"name": "wlkcid", "value": c['wlkcid']}]}
    if c['_type'] == 'student':
        hws = get_json('/b/wlxt/kczy/zy/student/zyListWj', data)['object']['aaData']\
            + get_json('/b/wlxt/kczy/zy/student/zyListYjwg', data)['object']['aaData']\
            + get_json('/b/wlxt/kczy/zy/student/zyListYpg', data)['object']['aaData']
    else:
        hws = get_json('/b/wlxt/kczy/zy/teacher/pageList', data)['object']['aaData']
    for hw in hws:
        path = os.path.join(pre, escape(hw['bt']))
        if not os.path.exists(path): os.makedirs(path)
        if c['_type'] == 'student':
            open(os.path.join(path, 'info.txt'), 'w', encoding='utf-8').write('%s\n状态：%s\n开始时间：%s\n截止时间：%s\n上传时间：%s\n批阅状态：%s\n批阅时间：%s\n批阅内容：%s\n成绩：%s\n批阅者：%s %s\n' \
                % (hw['bt'], hw['zt'], hw['kssjStr'], hw['jzsjStr'], hw['scsjStr'], hw['pyzt'], hw['pysjStr'], hw['pynr'], hw['cj'], hw['gzzh'], hw['jsm']))
            page = bs(get_page('/f/wlxt/kczy/zy/student/viewCj?wlkcid=%s&zyid=%s&xszyid=%s' % (hw['wlkcid'], hw['zyid'], hw['xszyid'])), 'html.parser')
            files = page.findAll(class_='wdhere')
            for f in files:
                os.chdir(path) # to avoid filename too long
                download('/b/wlxt/kczy/zy/%s/downloadFile/%s/%s' % (c['_type'], hw['wlkcid'], f.findAll('a')[-1].attrs['onclick'].split("ZyFile('")[-1][:-2]), name=f.findAll('a')[0].text)
                os.chdir(now)
        else:
            print(hw['bt'])
            data = {'aoData': [{"name": "wlkcid", "value": c['wlkcid']}, {"name": "zyid", "value": hw['zyid']}]}
            info_str = '学号,姓名,院系,班级,上交时间,状态,成绩,批阅老师\n'
            stus = get_json('/b/wlxt/kczy/xszy/teacher/getDoneInfo', data)['object']['aaData']
            for stu in stus:
                info_str += '%s,%s,%s,%s,%s,%s,%s,%s\n' % (stu['xh'], stu['xm'], stu['dwmc'], stu['bm'], stu['scsjStr'], stu['zt'], stu['cj'], stu['jsm'])
                page = bs(get_page('/f/wlxt/kczy/xszy/teacher/beforePiYue?wlkcid=%s&xszyid=%s' % (stu['wlkcid'], stu['xszyid'])), 'html.parser')
                files = page.findAll(class_='wdhere')
                for f in files:
                    if f.text == '\n':
                        continue
                    os.chdir(path) # to avoid filename too long
                    try:
                        id = f.findAll('span')[0].attrs['onclick'].split("'")[1]
                        name = f.findAll('span')[0].text
                    except:
                        id = f.findAll('a')[-1].attrs['onclick'].split("'")[1]
                        name = f.findAll('a')[0].text
                    download('/b/wlxt/kczy/xszy/teacher/downloadFile/%s/%s' % (stu['wlkcid'], id), name=stu['xh']+'_'+name)
                    os.chdir(now)
            stus = get_json('/b/wlxt/kczy/xszy/teacher/getUndoInfo', data)['object']['aaData']
            for stu in stus:
                info_str += '%s,%s,%s,%s,%s,%s,%s,%s\n' % (stu['xh'], stu['xm'], stu['dwmc'], stu['bm'], stu['scsjStr'], stu['zt'], stu['cj'], stu['jsm'])
            open(os.path.join(path, 'info.csv'), 'w', encoding='utf-8').write(info_str)

def build_discuss(s):
    disc = '课程：%s\n内容：%s\n学号：%s\n姓名：%s\n发布时间:%s\n最后回复：%s\n回复时间：%s\n' % (s['kcm'], s['bt'], s['fbr'], s['fbrxm'], s['fbsj'], s['zhhfrxm'], s['zhhfsj'])
    return disc

def sync_discuss(c):
    pre = os.path.join(c['kcm'], '讨论')
    if not os.path.exists(pre): os.makedirs(pre)
    try:
        disc = get_json('/b/wlxt/bbs/bbs_tltb/%s/kctlList?wlkcid=%s' % (c['_type'], c['wlkcid']))['object']['resultsList']
    except:
        return
    for d in disc:
        filename = os.path.join(pre, escape(d['bt']) + '.txt')
        if os.path.exists(filename):
            continue
        try:
            html = get_page('/f/wlxt/bbs/bbs_tltb/%s/viewTlById?wlkcid=%s&id=%s&tabbh=2&bqid=%s' % (c['_type'], d['wlkcid'], d['id'], d['bqid']))
            open(filename, 'w').write(build_discuss(d) + bs(html, 'html.parser').find(class_='detail').text)
        except:
            pass

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action='store_true')
    parser.add_argument("--semester", nargs='+', type=str, default=[])
    parser.add_argument("--ignore", nargs='+', type=str, default=[])
    parser.add_argument("--course", nargs='+', type=str, default=[])
    args = parser.parse_args()
    if os.path.exists('.pass'):
        username, password = open('.pass', encoding='utf-8').read().split()
    else:
        username = input('username: ')
        password = getpass.getpass('password: ')
    if login(username, password):
        courses = get_courses(args)
        for c in courses:
            c['_type'] = {'0': 'teacher', '3': 'student'}[c['jslx']]
            print('Sync ' + c['xnxq'] + ' ' + c['kcm'])
            if not os.path.exists(c['kcm']): os.makedirs(c['kcm'])
            sync_info(c)
            sync_discuss(c)
            sync_notify(c)
            sync_file(c)
            sync_hw(c)
