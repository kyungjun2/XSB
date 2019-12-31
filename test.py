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


@app.route('/recent_articles', methods=['get'])
def recent_articles():
    import json
    import requests
    import xml.etree.ElementTree as ET

    def naver_recent_articles():
        # 0. 파라미터 확인
        blog_name = request.args.get('blogName')
        if blog_name is None:
            return render_template("dependencies.html", args=[{'name': 'blogName', 'value': blog_name, 'hint': '블로그 아이디'},
                                                              {'name': 'target', 'value': target, 'hint': '블로그 플랫폼'}])

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

    def tistory_recent_articles():
        # 0. 파라미터 확인
        try:
            token = session['tistory_token']
        except KeyError:
            token = None
        blog_name = request.args.get('blogName')

        if token is None or blog_name is None:
            return render_template("dependencies.html", args=[{'name': 'token', 'value': token, 'hint': '티스토리 로그인 필요'},
                                                              {'name': 'blogName', 'value': blog_name, 'hint': '블로그 아이디'},
                                                              {'name': 'target', 'value': target, 'hint': '블로그 플랫폼'}])

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

    target = str(request.args.get('target'))
    if target == "naver":
        return naver_recent_articles()
    elif target == "tistory":
        return tistory_recent_articles()
    else:
        return render_template("dependencies.html", args=[{'name': 'target', 'value': target, 'hint': '블로그 플랫폼'}])


@app.route('/read_article', methods=['get'])
def read_article():
    import json
    import requests
    from bs4 import BeautifulSoup as bs

    def tistory_read_article():
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
                                                              {'name': 'postId', 'value': post_id},
                                                              {'name': 'target', 'value': target, 'hint': '블로그 플랫폼'}])

        # 1. 요청
        url = "https://www.tistory.com/apis/post/read"
        param = {'access_token': token, 'blogName': blog_name, 'postId': post_id, 'output': 'json'}
        j = json.loads(requests.get(url=url, params=param).text)

        # 2. 파싱
        ret = {"title": j['tistory']['item']['title'], "content": j['tistory']['item']['content'],
               "writeDate": j['tistory']['item']['date'], "postUrl": j['tistory']['item']['postUrl']}
        return ret

    def naver_read_article():
        # 0. 파라미터 확인
        blog_name = request.args.get('blogName')
        post_id = request.args.get('postId')
        if blog_name is None or post_id is None:
            return render_template("dependencies.html", args=[{'name': 'blogName', 'value': blog_name},
                                                              {'name': 'postId', 'value': post_id},
                                                              {'name': 'target', 'value': target, 'hint': '블로그 플랫폼'}])

        # 1. 요청
        url = "https://blog.naver.com/PostView.nhn?blogId={0}&logNo={1}".format(blog_name, post_id)
        r = requests.get(url=url)
        soup = bs(r.text, "html.parser")

        # 2. 파싱
        try:  # 최신버전 smartEditor 대응
            content = str(soup.select_one("table#printPost1 div.se-main-container").prettify())
            title = soup.select_one("table#printPost1 div.se-title-text p").text
            writeDate = soup.select_one("table#printPost1 span.se_publishDate").text
        except (KeyError, AttributeError):
            try:   # 옛버전 smartEditor 대응
                title = soup.select_one("div.htitle span").text
                writeDate = soup.select_one("p.date").text
                content = str(soup.select_one("div#postViewArea").prettify())
            except (KeyError, AttributeError):  # API로 쓴 글 대응
                content = str(soup.select("table#printPost1 div.se_component_wrap")[1].prettify())
                title = soup.select_one("table#printPost1 div.se_title h3").text
                writeDate = soup.select_one("table#printPost1 span.se_publishDate").text

        return {'title': title, 'content': content, 'writeDate': writeDate, 'url': url}

    target = str(request.args.get('target'))
    if target == "naver":
        return naver_read_article()
    elif target == "tistory":
        return tistory_read_article()
    else:
        return render_template("dependencies.html", args=[{'name': 'target', 'value': target, 'hint': '블로그 플랫폼'}])


@app.route('/write_article', methods=['get'])
def write_article():
    import time
    import requests
    import keys

    def tistory_write_article():
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
                                                              {'name': 'writeDate', 'value': write_date},
                                                              {'name': 'target', 'value': target, 'hint': '블로그 플랫폼'}])

        # 1. 요청
        url = "https://www.tistory.com/apis/post/write"
        disclaimer = '''<div id="xsb-disclaimer><hr>원 글 작성일 : {0} <br /></div>"'''.format(write_date)
        param = {'access_token': token, 'output': 'json', 'blogName': blog_name, 'title': title, 'content': content + disclaimer,
                 'visibility': '3', 'published': str(int(time.time()))}

        r = requests.post(url=url, params=param)
        return r.text

    def naver_write_article():
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
                                                              {'name': 'writeDate', 'value': write_date},
                                                              {'name': 'target', 'value': target, 'hint': '블로그 플랫폼'}])

        # 1. 요청
        url = "	https://openapi.naver.com/blog/writePost.json"
        disclaimer = '''<div id="xsb-disclaimer><p>원 글 작성일 : {0} <br /></p></div>"'''.format(write_date)
        param = {'title': title, 'contents': content + disclaimer}
        print(param)

        header = {'Authorization': "Bearer " + token, 'X-Naver-Client-Id': keys.naver_app_id,
                  'X-Naver-Client-Secret': keys.naver_secret}

        r = requests.post(url=url, params=param, headers=header)
        return r.text

    target = str(request.args.get('target'))
    if target == "naver":
        return naver_write_article()
    elif target == "tistory":
        return tistory_write_article()
    else:
        return render_template("dependencies.html", args=[{'name': 'target', 'value': target, 'hint': '블로그 플랫폼'}])



### 이 밑은 개발용임 ###


@app.route('/')
def list_all():
    maps = app.url_map
    pages = maps._rules
    page_list = ""

    for rule in pages:
        page_list += "<a href={0}>{0}</a> | METHODS = {1} <br />".format(rule.rule, str(rule.methods))

    return page_list


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=12321, debug=True)
