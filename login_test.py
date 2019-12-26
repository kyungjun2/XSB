# Flask를 이용해 웹앱 제작

# Flask 작동법 (windows, CMD)
# 1. cd '프로젝트 폴더 경로'
# 2. set FLASK_APP='파이썬 파일 이름'
# 3. 'venv의 python 파일 경로'\python.exe -m flask run --host=0.0.0.0 --port=12321

from flask import Flask, request, redirect, session

import os
app = Flask(__name__)
app.secret_key = os.urandom(16)


@app.route('/tistory_login')
def tistory_auth_token():
    # 1단계 : Auth Code 요청
    import keys
    import requests

    url = "https://www.tistory.com/oauth/authorize"
    param = {'client_id': keys.tistory_app_id, 'redirect_uri': keys.tistory_callback_uri, 'response_type': 'code'}
    return redirect(requests.get(url, params=param).url, code=302)


@app.route('/tistory_auth_code', methods=['GET'])
def tistory_access_token():
    # 2단계 : Access Token 발급
    import keys
    import requests

    try:
        url = "https://www.tistory.com/oauth/access_token"
        param = {'client_id': keys.tistory_app_id, 'redirect_uri': keys.tistory_callback_uri,
                 'grant_type': 'authorization_code', 'client_secret': keys.tistory_secret,
                 'code': request.args.get('code')}
        r = requests.get(url, params=param)
        token = r.text.split('=')[1]
        session['tistory_token'] = token
        return session['tistory_token']
    except:
        return "Wrong Request."


@app.route('/naver_login')
def naver_auth_token():
    # 1단계 : Auth Code 요청
    import keys
    import requests

    url = "https://nid.naver.com/oauth2.0/authorize"
    param = {'client_id': keys.naver_app_id, 'redirect_uri': keys.naver_callback_uri, 'response_type': 'code',
             'state': '1'}
    return redirect(requests.get(url, params=param).url, code=302)


@app.route('/naver_auth_code', methods=['GET'])
def naver_access_token():
    # 2단계 : Access Token 발급
    import keys
    import requests
    import json

    try:
        url = "	https://nid.naver.com/oauth2.0/token"
        param = {'client_id': keys.naver_app_id, 'redirect_uri': keys.naver_callback_uri,
                 'grant_type': 'authorization_code', 'client_secret': keys.naver_secret,
                 'code': request.args.get('code'), 'state': '1'}
        r = json.loads(requests.get(url, params=param).text)
        session['naver_token'] = r['access_token']
        return session['naver_token']
    except:
        return "Wrong Request."


@app.route('/tistory_recent_articles', methods=['get'])
def tistory_recent_articles():
    import json
    import requests

    # 0. 파라미터 확인
    token = None
    blog_name = None

    try:
        token = session['tistory_token']
        blog_name = request.args.get('blogName')

        if blog_name is None:
            raise KeyError
    except KeyError:
        return "Wrong Request."

    # 1. 글 목록 받아오기
    url = "https://www.tistory.com/apis/post/list"
    param = {'access_token': token, 'output': 'json', 'blogName': blog_name, 'page': '1'}
    j = json.loads(requests.get(url, params=param).text)

    # 2. 글 목록 추출하기
    posts = j['tistory']['item']['posts']
    ret = []
    for post in posts:
        ret.append({str(post['id']): str(post['title'])})
    return {'return': ret}


@app.route('/naver_recent_articles', methods=['GET'])
def naver_recent_articles():
    import requests
    import xml.etree.ElementTree as ET

    blog_name = request.args.get('blogName')
    if blog_name is None:
        return "Wrong Request."

    ret = []
    url = "https://rss.blog.naver.com/{}.xml".format(blog_name)
    x = ET.fromstring(requests.get(url).text)
    for item in x.findall('./channel/item'):
        post = {}
        for child in item:
            if child.tag == "title" or child.tag == "link":
                post[child.tag] = child.text
        ret.append(post)

    return {'return': ret}


@app.route('/tistory_read_article', methods=['get'])
def tistory_read_article():
    import json
    import requests

    token = None
    blog_name = None
    post_id = None
    try:
        token = session['tistory_token']
        blog_name = request.args.get('blogName')
        post_id = request.args.get('postId')

        if blog_name is None or post_id is None:
            raise KeyError
    except KeyError:
        return "Wrong Request."

    url = "https://www.tistory.com/apis/post/read"
    param = {'access_token': token, 'blogName': blog_name, 'postId': post_id, 'output': 'json'}
    print(requests.get(url=url, params=param).text)

    j = json.loads(requests.get(url=url, params=param).text)
    return j


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
