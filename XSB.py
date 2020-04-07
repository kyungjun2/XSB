class XSBError(BaseException):
    def __init__(self, message):
        self.message = message


class XSB:
    def __init__(self):
        self.target = None
        self.credential = {}   # {블로그(tistory/naver): 토큰}
        self.blog_name = {}  # {블로그(tistory/naver): 아이디}

        self.target_posts = []  # [postid,...]
        self.downloaded_posts = []  # [{'title': 원글제목, 'postUrl': 원글주소, 'writeDate': 원글작성일, 'content': 내용},...]
        self.results = []

    def validate_stage(self, level):
        # 1단계 - 로그인
        try:
            temp = self.credential['naver']
            temp = self.credential['tistory']
        except KeyError:
            raise XSBError("잘못된 접근입니다.")

        # 2단계 - 목적지
        if self.target == 'naver':
            pass
        elif self.target == 'tistory':
            pass
        else:
            raise XSBError("잘못된 접근입니다.")

        if level == 3:  # 3단계 앞의 과정을 거쳤는지만 확인
            return

        # 3단계 - 최근 글 선택
        if not self.target_posts:
            raise XSBError("잘못된 접근입니다.")

        if level == 4:  # 4단계 앞의 과정을 거쳤는지만 확인
            return

        # 4단계 - 글 다운로드
        if not self.downloaded_posts:
            raise XSBError("잘못된 접근입니다.")

        if level == 5:  # 5단계 앞의 과정을 거쳤는지만 확인
            return

    def recent_post(self, target):
        self.validate_stage(level=3)
        if target == 'naver':
            import requests
            import xml.etree.ElementTree as ET

            posts = []
            url = "https://rss.blog.naver.com/{}.xml".format(self.blog_name['naver'])
            x = ET.fromstring(requests.get(url).text)

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
            return posts

        elif target == 'tistory':
            import json
            import requests

            url = "https://www.tistory.com/apis/post/list"
            param = {'access_token': self.credential['tistory'], 'output': 'json',
                     'blogName': self.blog_name['tistory'], 'page': '1'}
            j = json.loads(requests.get(url, params=param).text)

            posts = j['tistory']['item']['posts']
            ret = []
            for post in posts:
                ret.append(
                    {'postLink': str(post['postUrl']), 'title': str(post['title']), 'writeDate': str(post['date']),
                     'postId': str(post['postUrl']).split('/')[-1]})
            return ret
        else:
            raise XSBError("잘못된 접근입니다.")

    def download_post(self, post_list):
        import json
        import requests
        from bs4 import BeautifulSoup as bs
        import config
        import platform
        from pathlib import Path
        self.validate_stage(level=4)

        if self.target == 'naver':
            def download_tistory(postid):
                # 1. 요청
                url = "https://www.tistory.com/apis/post/read"
                param = {'access_token': self.credential['tistory'], 'blogName': self.blog_name['tistory'],
                         'postId': postid, 'output': 'json'}
                j = json.loads(requests.get(url=url, params=param).text)

                # 2. 이미지 다운로드
                content = j['tistory']['item']['content']

                path = config.file_save_path + "{0}\\{1}\\{2}\\".format('tistory', self.blog_name['tistory'], postid)\
                    if platform.system() == "Windows" \
                    else "{0}/{1}/{2}/".format('tistory', self.blog_name['tistory'], postid)
                Path(path).mkdir(parents=True, exist_ok=True)

                idx = 0
                image_data = {}
                soup = bs(content, 'html.parser')
                for img in soup.find_all("img"):
                    img = img.attrs['src']
                    try:
                        img = img.split("kage@")[1]
                        req = requests.get("https://k.kakaocdn.net/dn/" + img, allow_redirects=True)
                    except IndexError:
                        req = requests.get(img, allow_redirects=True)
                        req.url = req.url.split('?')[-1]

                    with open(path + str(idx) + "." + req.url.split('.')[-1], 'wb') as fs:
                        fs.write(req.content)
                        fs.close()
                    image_data[str(idx) + "." + req.url.split('.')[-1]] = req.headers['content-type']
                    idx += 1

                with open(path + 'images.json', 'w') as file:
                    json.dump({"images": image_data}, file)
                    file.close()

                # 3. 결과 리턴
                ret = {'title': j['tistory']['item']['title'], 'content': content,
                       'writeDate': j['tistory']['item']['date'], 'postUrl': j['tistory']['item']['postUrl']}
                return ret

            results = []
            for post in post_list:
                results.append(download_tistory(post))
            self.downloaded_posts = results
            return results

        elif self.target == 'tistory':
            def download_naver(postid):
                # 1. 요청
                url = "https://blog.naver.com/PostView.nhn?blogId={0}&logNo={1}".format(self.blog_name['naver'], postid)
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
                path = config.file_save_path + "{0}\\{1}\\{2}\\".format('naver', self.blog_name['naver'], postid) \
                    if platform.system() == "Windows" \
                    else "{0}/{1}/{2}/".format('naver', self.blog_name['naver'], postid)
                Path(path).mkdir(parents=True, exist_ok=True)

                for img in soup.find_all("img"):
                    url = img.attrs['src'] if img.attrs['src'] is not None else img.attrs['data-lazy-src']
                    url = url.split('?type')[0]
                    req = requests.get(url + ("?type=w1" if url.count("postfiles") != 0 else ""), allow_redirects=True)
                    with open(path + str(idx) + "." + url.split('.')[-1], 'wb') as fs:
                        fs.write(req.content)
                        fs.close()

                    image_data[str(idx) + "." + req.url.split('.')[-1]] = req.headers['content-type']
                    img_urls.append(url)
                    idx += 1
                with open(path + 'images.json', 'w') as file:
                    json.dump({"images": image_data}, file)
                    file.close()

                # 3. 결과 리턴
                ret = {'title': title, 'content': content, 'writeDate': writeDate, 'postUrl': url}
                return ret

            results = []
            for post in post_list:
                results.append(download_naver(post))
            self.downloaded_posts = results
            return results
        else:
            raise XSBError("잘못된 접근입니다.")

    def upload_post(self):
        import time
        import requests
        import config
        import json
        import platform
        import os
        import keys
        from bs4 import BeautifulSoup as bs
        self.validate_stage(level=5)


        if self.target == 'naver':
            def naver_write_article(post, postid):
                # 1. 업로드 해야하는 사진이 있는지 확인
                path = config.file_save_path + "{0}\\{1}\\{2}\\".format('tistory', self.blog_name['tistory'], postid)\
                    if platform.system() == "Windows" \
                    else "{0}/{1}/{2}/".format('tistory', self.blog_name['tistory'], postid)
                files = []

                with open(path + "images.json", 'r') as fs:
                    file_type = json.load(fs)
                    fs.close()
                if len(file_type['images']) != 0:
                    # 1-1. 이미지 준비
                    for img in os.listdir(path):
                        if img == "images.json":
                            continue
                        files.append(('image', (img, open(path + img, "rb"), file_type['images'][img])))

                    # 1-2. 이미지 링크 교체
                    soup = bs(post['content'], 'html.parser')
                    idx = 0
                    for img in soup.find_all("img"):
                        img.attrs['src'] = f"#{idx}"
                        idx += 1
                    post['content'] = soup.prettify()

                # 2. 요청
                url = "	https://openapi.naver.com/blog/writePost.json"
                disclaimer = '''<div id="xsb-disclaimer><p>원 글 작성일 : {0} <br /></p></div>"'''.format(post['writeDate'])
                param = {'title': post['title'], 'contents': post['content'], }

                header = {'Authorization': "Bearer " + self.credential['naver'], 'X-Naver-Client-Id': keys.naver_app_id,
                          'X-Naver-Client-Secret': keys.naver_secret}

                if len(files) == 0:
                    r = requests.post(url=url, data=param, headers=header)
                else:
                    print(files)
                    r = requests.post(url=url, data=param, headers=header, files=files)
                    print(r.request)

                # 1-3. 업로드한 이미지 삭제
                for file in files:
                    fs = file[1][1]
                    fs.close()

                for file in os.listdir(path):
                    os.remove(path + file)
                os.rmdir(path)
                return r.text

            for post in self.downloaded_posts:
                postid = post['postUrl'][post['postUrl'].index(post['postUrl'].split('/')[-1]):]
                print(naver_write_article(post, postid))

        elif self.target == 'tistory':
            def tistory_write_article(post, postid):
                # 1. 이미지 업로드 (있으면)
                url = "https://www.tistory.com/apis/post/attach"
                param = {'access_token': self.credential['tistory'], 'blogName': self.blog_name['tistory'], 'output': 'json'}

                path = config.file_save_path + "{0}\\{1}\\{2}\\".format('naver', self.blog_name['naver'], postid)\
                    if platform.system() == "Windows" \
                    else "{0}/{1}/{2}/".format('naver', self.blog_name['naver'], postid)

                with open(path + "images.json", 'r') as fs:
                    file_type = json.load(fs)
                    fs.close()
                if len(file_type['images']) != 0:
                    image_urls = []

                    # 1-1. 이미지 업로드
                    for img in os.listdir(path):
                        if img == "images.json":
                            continue

                        file = {'uploadedfile': (img, open(path + img, "rb"))}
                        j = json.loads(requests.post(url=url, params=param, files=file).text)
                        image_urls.append(j['tistory']['replacer'])
                        file['uploadedfile'][1].close()

                    # 1-2. 이미지 링크 교체
                    soup = bs(post['content'], "html.parser")
                    idx = 0

                    for tag in soup.find_all("img"):
                        tag.parent.insert(tag.parent.index(tag) + 1, image_urls[idx])
                        idx += 1
                        tag.decompose()
                    post['content'] = soup.prettify()

                    # 1-3. 업로드한 이미지 삭제
                    for file in os.listdir(path):
                        os.remove(path + file)
                    os.rmdir(path)

                # 2. 요청
                url = "https://www.tistory.com/apis/post/write"
                disclaimer = '''<div id="xsb-disclaimer><hr>원 글 작성일 : {0} <br /></div>"'''.format(post['writeDate'])
                param = {'access_token': self.credential['tistory'], 'output': 'json', 'blogName': self.blog_name['tistory'],
                         'title': post['title'],
                         'content': post['content'],
                         'visibility': '3', 'published': str(int(time.time()))}

                r = requests.post(url=url, data=param)
                return r.text

            for post in self.downloaded_posts:
                postid = post['postUrl'][post['postUrl'].index(post['postUrl'].split('=')[-1]):]
                print(tistory_write_article(post, postid))
        else:
            raise XSBError("잘못된 접근입니다.")
