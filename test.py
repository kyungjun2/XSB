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
            return render_template("dependencies.html",
                                   args=[{'name': 'blogName', 'value': blog_name, 'hint': '블로그 아이디'},
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
                    post['postId'] = child.text.split('/')[-1]
                elif child.tag == "pubDate":
                    post['writeDate'] = child.text
            posts.append(post)

        return render_template("recent_articles.html", posts=posts, blog={'type': 'naver', 'name': blog_name})

    def tistory_recent_articles():
        # 0. 파라미터 확인
        try:
            token = session['tistory_token']
        except KeyError:
            token = None
        blog_name = request.args.get('blogName')

        if token is None or blog_name is None:
            return render_template("dependencies.html", args=[{'name': 'token', 'value': token, 'hint': '티스토리 로그인 필요'},
                                                              {'name': 'blogName', 'value': blog_name,
                                                               'hint': '블로그 아이디'},
                                                              {'name': 'target', 'value': target, 'hint': '블로그 플랫폼'}])

        # 1. 요청
        url = "https://www.tistory.com/apis/post/list"
        param = {'access_token': token, 'output': 'json', 'blogName': blog_name, 'page': '1'}
        j = json.loads(requests.get(url, params=param).text)

        # 2. 파싱
        posts = j['tistory']['item']['posts']
        ret = []
        for post in posts:
            ret.append({'postLink': str(post['postUrl']), 'title': str(post['title']), 'writeDate': str(post['date']),
                        'postId': str(post['postUrl']).split('/')[-1]})

        return render_template("recent_articles.html", posts=ret, blog={'type': 'tistory', 'name': blog_name})

    target = str(request.args.get('target'))
    if target == "naver":
        return naver_recent_articles()
    elif target == "tistory":
        return tistory_recent_articles()
    else:
        return render_template("dependencies.html", args=[{'name': 'target', 'value': target, 'hint': '블로그 플랫폼'}])


@app.route('/selected_article', methods=['post'])
def selected_articles():
    posts = []

    # 0.  파라미터 확인
    target = request.form.get('target')
    blog_name = request.form.get('blogName')
    if target == 'naver':
        tistory_blog_name = request.form.get('tistory-blog-name')

    # 1. 선택된 글 받아오기
    for post_id in request.form.getlist('selection[]'):
        posts.append(read_article(args={'target': target, 'postId': post_id, 'blogName': blog_name}))

    # 2. 다른 플랫폼에 글 작성
    ret = ""
    for post in posts:
        if target == "tistory":  # 네이버로 글 복사
            arg = {'target': 'naver', 'title': post['title'], 'content': post['content'],
                   'writeDate': post['writeDate']}
            try:
                arg['imgPath'] = post['image_path']
            except KeyError:
                pass
            ret += str(write_article(args=arg))
        elif target == "naver":  # 티스토리로 글 복사
            arg = {'target': 'tistory', 'title': post['title'], 'content': post['content'],
                   'writeDate': post['writeDate'], 'blogName': tistory_blog_name}
            try:
                arg['imgPath'] = post['image_path']
            except KeyError:
                pass
            ret += str(write_article(args=arg))

    return ret


@app.route('/read_article', methods=['get'])
def read_article(args=None):
    import json
    import requests
    from bs4 import BeautifulSoup as bs
    import re
    import config
    import platform
    from pathlib import Path

    def tistory_read_article():
        # 0. 파라미터 확인
        try:
            token = session['tistory_token']
        except KeyError:
            token = None

        if args is None:
            blog_name = request.args.get('blogName')
            post_id = request.args.get('postId')
        else:
            blog_name = args['blogName']
            post_id = args['postId']

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
        # 2-1. 이미지 다운로드
        r = re.compile("""\[##_Image\|kage@([a-zA-Z0-9/.]+).+_##\]""")
        r2 = re.compile("""(\[##_Image\|kage@[a-zA-Z0-9/.]+.+_##\])""")
        content = j['tistory']['item']['content']

        img_urls = []
        idx = 0
        image_data = {}

        path = config.file_save_path + "{0}\\{1}\\{2}\\".format(target, blog_name,
                                                                post_id) if platform.system() == "Windows" \
            else "{0}/{1}/{2}/".format(target, blog_name, post_id)
        Path(path).mkdir(parents=True, exist_ok=True)

        for img in r.findall(content):
            req = requests.get("https://k.kakaocdn.net/dn/" + img, allow_redirects=True)
            open(path + str(idx) + "." + img.split('.')[-1], 'wb').write(req.content)

            img_urls.append("https://k.kakaocdn.net/dn/" + img)
            image_data[str(idx) + "." + url.split('.')[-1]] = req.headers['content-type']
            img_urls.append(url)
            idx += 1
        with open(path + 'images.json', 'w') as file:
            json.dump(image_data, file)

        # 2-2. 링크 교체
        content = r2.sub("""<img src="">""", content)
        soup = bs(content, 'html.parser')
        idx = 0
        for img in soup.find_all("img"):
            img.attrs['source'] = img_urls[idx]
            idx += 1

        # 3. 결과 리턴
        ret = {'title': j['tistory']['item']['title'], 'content': content,
               'writeDate': j['tistory']['item']['date'], 'postUrl': j['tistory']['item']['postUrl']}
        if len(img_urls) != 0:
            ret['image_path'] = path
        return ret

    def naver_read_article():
        # 0. 파라미터 확인
        if args is None:
            blog_name = request.args.get('blogName')
            post_id = request.args.get('postId')
        else:
            blog_name = args['blogName']
            post_id = args['postId']

        if blog_name is None or post_id is None:
            return render_template("dependencies.html", args=[{'name': 'blogName', 'value': blog_name},
                                                              {'name': 'postId', 'value': post_id},
                                                              {'name': 'target', 'value': target, 'hint': '블로그 플랫폼'}])

        # 1. 요청
        url = "https://blog.naver.com/PostView.nhn?blogId={0}&logNo={1}".format(blog_name, post_id)
        r = requests.get(url=url)
        soup = bs(r.text, "html.parser")

        # 2. 파싱
        # 2-1. 글 내용 파싱
        try:  # 최신버전 smartEditor 대응
            content = str(soup.select_one("table#printPost1 div.se-main-container").prettify())
            title = soup.select_one("table#printPost1 div.se-title-text p").text
            writeDate = soup.select_one("table#printPost1 span.se_publishDate").text
        except (KeyError, AttributeError):
            try:  # 옛버전 smartEditor 대응
                title = soup.select_one("div.htitle span").text
                writeDate = soup.select_one("p.date").text
                content = str(soup.select_one("div#postViewArea").prettify())
            except (KeyError, AttributeError):  # API로 쓴 글 대응
                content = str(soup.select("table#printPost1 div.se_component_wrap")[1].prettify())
                title = soup.select_one("table#printPost1 div.se_title h3").text
                writeDate = soup.select_one("table#printPost1 span.se_publishDate").text

        # 2-2. 이미지 다운로드
        idx = 0
        img_urls = []
        image_data = {}

        soup = bs(content, "html.parser")
        path = config.file_save_path + "{0}\\{1}\\{2}\\".format(target, blog_name,
                                                                post_id) if platform.system() == "Windows" \
            else "{0}/{1}/{2}/".format(target, blog_name, post_id)
        Path(path).mkdir(parents=True, exist_ok=True)

        for img in soup.find_all("img"):
            url = img.attrs['src'] if img.attrs['src'] is not None else img.attrs['data-lazy-src']
            url = url.split('?type')[0]
            req = requests.get(url + ("?type=w1" if url.count("postfiles") != 0 else ""), allow_redirects=True)
            open(path + str(idx) + "." + url.split('.')[-1], 'wb').write(req.content)

            image_data[str(idx) + "." + url.split('.')[-1]] = req.headers['content-type']
            img_urls.append(url)
            idx += 1
        with open(path + 'images.json', 'w') as file:
            json.dump(image_data, file)

        # 3. 결과 리턴
        ret = {'title': title, 'content': content, 'writeDate': writeDate, 'url': url}
        if len(img_urls) != 0:
            ret['image_path'] = path
        return ret

    if args is None:
        target = str(request.args.get('target'))
    else:
        target = args['target']

    if target == "naver":
        return naver_read_article()
    elif target == "tistory":
        return tistory_read_article()
    else:
        return render_template("dependencies.html", args=[{'name': 'target', 'value': target, 'hint': '블로그 플랫폼'}])


@app.route('/write_article', methods=['post'])
def write_article(args=None):
    import time
    import requests
    import keys
    import json
    from bs4 import BeautifulSoup as bs

    def tistory_write_article():
        # 0. 파라미터 확인
        try:
            token = session['tistory_token']
        except KeyError:
            token = None

        if args is None:
            blog_name = request.form.get('blogName')
            content = request.form.get('content')
            title = request.form.get('title')
            write_date = request.form.get('writeDate')
            image_path = request.form.get('imgPath')
        else:
            blog_name = args['blogName']
            content = args['content']
            title = args['title']
            write_date = args['writeDate']
            try:
                image_path = args['imgPath']
            except KeyError:
                image_path = None

        if token is None or blog_name is None or content is None or content is None \
                or write_date is None or title is None:
            return render_template("dependencies.html", args=[{'name': 'token', 'value': token},
                                                              {'name': 'blogName', 'value': blog_name},
                                                              {'name': 'content', 'value': content},
                                                              {'name': 'title', 'value': title},
                                                              {'name': 'writeDate', 'value': write_date},
                                                              {'name': 'target', 'value': target, 'hint': '블로그 플랫폼'}])

        # 1. 이미지 업로드 (있으면)
        url = "https://www.tistory.com/apis/post/attach"
        param = {'access_token': token, 'blogName': blog_name, 'output': 'json'}

        if image_path is not None:
            file_type = json.load(open(image_path + "images.json", 'r'))
            image_urls = []

            # 1. 이미지 업로드
            for img in os.listdir(image_path):
                if img == "images.json":
                    continue
                file = {'uploadedfile': (img, open(image_path + img, "rb"))}
                j = json.loads(requests.post(url=url, params=param, files=file).text)
                image_urls.append(j['tistory']['replacer'])

            # 2. 이미지 링크 교체
            soup = bs(content, "html.parser")
            idx = 0

            for tag in soup.find_all("img"):
                tag.parent.insert(tag.parent.index(tag) + 1, image_urls[idx])
                idx += 1
                tag.decompose()
            content = soup.prettify()

            # 3. 업로드한 이미지 삭제
            for file in os.listdir(image_path):
                os.remove(image_path + file)
            os.rmdir(image_path)
            try:
                post_path = image_path[:image_path.index(image_path.split("\\")[-2])]
                blog_path = post_path[:post_path.index(post_path.split("\\")[-2])]
                os.rmdir(post_path)
                os.rmdir(blog_path)
            except PermissionError:
                pass
            except Exception as e:
                print(e)
                print(image_path)

        # 2. 요청
        url = "https://www.tistory.com/apis/post/write"
        disclaimer = '''<div id="xsb-disclaimer><hr>원 글 작성일 : {0} <br /></div>"'''.format(write_date)
        param = {'access_token': token, 'output': 'json', 'blogName': blog_name, 'title': title, 'content': content,
                 'visibility': '3', 'published': str(int(time.time()))}

        r = requests.post(url=url, data=param)
        return r.text

    def naver_write_article():
        # 0. 파라미터 확인
        try:
            token = session['naver_token']
        except KeyError:
            token = None
        if args is None:
            content = request.form.get('content')
            title = request.form.get('title')
            write_date = request.form.get('writeDate')
        else:
            content = args['content']
            title = args['title']
            write_date = args['writeDate']

        if token is None or content is None or content is None or write_date is None or title is None:
            return render_template("dependencies.html", args=[{'name': 'token', 'value': token},
                                                              {'name': 'content', 'value': content},
                                                              {'name': 'title', 'value': title},
                                                              {'name': 'writeDate', 'value': write_date},
                                                              {'name': 'target', 'value': target, 'hint': '블로그 플랫폼'}])

        # 1. 요청
        url = "	https://openapi.naver.com/blog/writePost.json"
        disclaimer = '''<div id="xsb-disclaimer><p>원 글 작성일 : {0} <br /></p></div>"'''.format(write_date)
        param = {'title': title, 'contents': content}

        header = {'Authorization': "Bearer " + token, 'X-Naver-Client-Id': keys.naver_app_id,
                  'X-Naver-Client-Secret': keys.naver_secret}

        r = requests.post(url=url, data=param, headers=header)
        return r.text

    if args is None:
        target = str(request.args.get('target'))
    else:
        target = args['target']

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
