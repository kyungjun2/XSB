# Flask를 이용해 웹앱 제작

# Flask 작동법 (windows, CMD)
# 1. cd '프로젝트 폴더 경로'
# 2. set FLASK_APP='파이썬 파일 이름'
# 3. 'venv의 python 파일 경로'\python.exe -m flask run --host=0.0.0.0 --port=12321

from flask import Flask, request, redirect, session, render_template

import os

app = Flask(__name__)
app.secret_key = os.urandom(16)


@app.route('/tistory_auth_code', methods=['GET'])
def tistory_access_token():
    import keys
    import requests

    if request.args.get('code') is None:
        # 1단계 : Auth Code 요청
        url = "https://www.tistory.com/oauth/authorize"
        param = {'client_id': keys.tistory_app_id, 'redirect_uri': keys.tistory_callback_uri, 'response_type': 'code'}
        return redirect(requests.get(url, params=param).url, code=302)
    else:
        # 2단계 : Access Token 발급
        try:
            url = "https://www.tistory.com/oauth/access_token"
            param = {'client_id': keys.tistory_app_id, 'redirect_uri': keys.tistory_callback_uri,
                     'grant_type': 'authorization_code', 'client_secret': keys.tistory_secret,
                     'code': request.args.get('code')}
            r = requests.get(url, params=param)
            if r.text.count("invalid_request") is not 0:
                raise IndexError

            token = r.text.split('=')[1]
            session['tistory_token'] = token
            return "로그인 성공"

        except (IndexError, ValueError):
            return "로그인 실패"


@app.route('/naver_auth_code', methods=['GET'])
def naver_access_token():
    import keys
    import requests
    import json

    if request.args.get('code') is None:
        # 1단계 : Auth Code 요청
        url = "https://nid.naver.com/oauth2.0/authorize"
        param = {'client_id': keys.naver_app_id, 'redirect_uri': keys.naver_callback_uri, 'response_type': 'code',
                 'state': '1'}
        return redirect(requests.get(url, params=param).url, code=302)

    else:
        # 2단계 : Access Token 발급
        try:
            url = "	https://nid.naver.com/oauth2.0/token"
            param = {'client_id': keys.naver_app_id, 'redirect_uri': keys.naver_callback_uri,
                     'grant_type': 'authorization_code', 'client_secret': keys.naver_secret,
                     'code': request.args.get('code'), 'state': '1'}
            r = json.loads(requests.get(url, params=param).text)
            session['naver_token'] = r['access_token']
            return "로그인 성공"
        except KeyError:
            return "로그인 실패"


@app.route('/tistory_recent_articles', methods=['get'])
def tistory_recent_articles():
    import json
    import requests

    # 0. 파라미터 확인
    try:
        token = session['tistory_token']
    except KeyError:
        token = None
    blog_name = request.args.get('blogName')

    if token is None or blog_name is None:
        return render_template("dependencies.html", args=[{'name': 'token', 'value': token},
                                                          {'name': 'blogName', 'value': blog_name}])

    # 1. 요청
    url = "https://www.tistory.com/apis/post/list"
    param = {'access_token': token, 'output': 'json', 'blogName': blog_name, 'page': '1'}
    j = json.loads(requests.get(url, params=param).text)

    # 2. 파싱
    posts = j['tistory']['item']['posts']
    ret = []
    for post in posts:
        ret.append({'postLink': str(post['postUrl']), 'title': str(post['title']), 'writeDate': str(post['date'])})

    return render_template("recent_articles.html", posts=ret)


@app.route('/naver_recent_articles', methods=['GET'])
def naver_recent_articles():
    import requests
    import xml.etree.ElementTree as ET

    # 0. 파라미터 확인
    blog_name = request.args.get('blogName')
    if blog_name is None:
        return render_template("dependencies.html", args=[{'name': 'blogName', 'value': blog_name}])

    # 1. 요청
    posts = []
    url = "https://rss.blog.naver.com/{}.xml".format(blog_name)
    x = ET.fromstring(requests.get(url).text)

    # 2. 파싱
    for item in x.findall('./channel/item'):
        post = {}
        for child in item:
            if child.tag == "title":
                post['title'] = child.text
            elif child.tag == "link":
                post['postLink'] = child.text
            elif child.tag == "pubDate":
                post['writeDate'] = child.text
        posts.append(post)

    return render_template("recent_articles.html", posts=posts)


@app.route('/tistory_read_article', methods=['get'])
def tistory_read_article():
    import json
    import requests

    # 0. 파라미터 확인
    try:
        token = session['tistory_token']
    except KeyError:
        token = None
    blog_name = request.args.get('blogName')
    post_id = request.args.get('postId')

    if token is None or blog_name is None or post_id is None:
        return render_template("dependencies.html", args=[{'name': 'token', 'value': token},
                                                          {'name': 'blogName', 'value': blog_name},
                                                          {'name': 'post_id', 'value': post_id}])

    # 1. 요청
    url = "https://www.tistory.com/apis/post/read"
    param = {'access_token': token, 'blogName': blog_name, 'postId': post_id, 'output': 'json'}
    j = json.loads(requests.get(url=url, params=param).text)

    # 2. 파싱
    ret = {"title": j['tistory']['item']['title'], "content": j['tistory']['item']['content'],
           "writeDate": j['tistory']['item']['date'], "postUrl": j['tistory']['item']['postUrl']}
    return ret


@app.route('/naver_read_article', methods=['get'])
def naver_read_article():
    from bs4 import BeautifulSoup as bs
    import requests

    # 0. 파라미터 확인
    blog_name = request.args.get('blogName')
    post_id = request.args.get('postId')
    if blog_name is None or post_id is None:
        return render_template("dependencies.html", args=[{'name': 'blogName', 'value': blog_name},
                                                          {'name': 'post_id', 'value': post_id}])

    # 1. 요청
    url = "https://blog.naver.com/PostView.nhn?blogId={0}&logNo={1}".format(blog_name, post_id)
    r = requests.get(url=url)
    soup = bs(r.text, "html.parser")

    # 2. 파싱
    try:  # 최신버전 smartEditor 대응
        content = str(soup.select_one("table#printPost1 div.se-main-container").prettify())
        title = soup.select_one("table#printPost1 div.se-title-text p").text
        writeDate = soup.select_one("table#printPost1 span.se_publishDate").text
    except (KeyError, AttributeError):  # 옛버전 smartEditor 대응
        title = soup.select_one("div.htitle span").text
        writeDate = soup.select_one("p.date").text
        content = soup.select_one("div.postViewArea")

    return {'title': title, 'content': content, 'writeDate': writeDate, 'url': url}


@app.route('/tistory_write_article', methods=['get'])
def tistory_write_article():
    import requests
    import time

    # 0. 파라미터 확인
    try:
        token = session['tistory_token']
    except KeyError:
        token = None
    blog_name = request.args.get('blogName')
    content = request.args.get('content')
    title = request.args.get('title')
    write_date = request.args.get('writeDate')

    if token is None or blog_name is None or content is None or content is None or write_date is None or title is None:
        return render_template("dependencies.html", args=[{'name': 'token', 'value': token},
                                                          {'name': 'blogName', 'value': blog_name},
                                                          {'name': 'content', 'value': content},
                                                          {'name': 'title', 'value': title},
                                                          {'name': 'writeDate', 'value': write_date}])

    # 1. 요청
    url = "https://www.tistory.com/apis/post/write"
    param = {'access_token': token, 'output': 'json', 'blogName': blog_name, 'title': title, 'content': content,
             'visibility': '3', 'published': str(int(time.time()))}

    r = requests.post(url=url, params=param)
    return r.text


@app.route('/naver_write_article', methods=['get'])
def naver_write_article():
    import requests
    import keys

    # 0. 파라미터 확인
    try:
        token = session['naver_token']
    except KeyError:
        token = None
    content = request.args.get('content')
    title = request.args.get('title')
    write_date = request.args.get('writeDate')

    if token is None or content is None or content is None or write_date is None or title is None:
        return render_template("dependencies.html", args=[{'name': 'token', 'value': token},
                                                          {'name': 'content', 'value': content},
                                                          {'name': 'title', 'value': title},
                                                          {'name': 'writeDate', 'value': write_date}])

    # 1. 요청
    url = "	https://openapi.naver.com/blog/writePost.json"
    param = {'title': title, 'contents': content}
    header = {'Authorization': "Bearer " + token, 'X-Naver-Client-Id': keys.naver_app_id,
              'X-Naver-Client-Secret': keys.naver_secret}

    r = requests.post(url=url, params=param, headers=header)
    return r.text


### 이 밑은 개발용임 ###


@app.route('/')
def list_all():
    maps = app.url_map
    pages = maps._rules
    page_list = ""

    for rule in pages:
        page_list += "<a href={0}>{0}</a> | METHODS = {1} <br />".format(rule.rule, str(rule.methods))

    return page_list


@app.route('/check_sessions')
def read_all_session():
    ret = ''
    for key in session.keys():
        ret += key + ': ' + session[key] + '<br />'
    return ret


@app.route('/append_session', methods=['get'])
def add_session():
    from flask import url_for
    if request.args.get('key') is not None and request.args.get('value') is not None:
        session[request.args.get('key')] = request.args.get('value')
    return redirect(url_for('read_all_session'))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=12321, debug=True)
