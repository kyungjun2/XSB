from flask import Flask
import os

app = Flask(__name__)
app.secret_key = os.urandom(16)
clients = {}


@app.route('/')
def welcome():
    from flask import render_template
    return render_template('index.html')


@app.route('/xsb', methods=['GET', 'POST'])
def main():
    from flask import session, render_template, request, redirect, url_for
    from XSB import XSB, XSBError

    xsb = XSB()
    try:
        # 이전에 만들어둔 값이 있으면 로그인 과정 무시
        xsb.__dict__ = clients[session['xsb']]
    except KeyError:
        # 1. 로그인
        try:
            xsb.credential['naver'] = session['naver_token']
            xsb.blog_name['naver'] = session['naver_name']
        except KeyError:
            return render_template('login.html', target='naver')
        try:
            xsb.credential['tistory'] = session['tistory_token']
            xsb.blog_name['tistory'] = session['tistory_name']
        except KeyError:
            return render_template('login.html', target='tistory')

        while True:
            session['xsb'] = os.urandom(16)
            if session['xsb'] not in clients.keys():
                clients[session['xsb']] = xsb.__dict__
                break
            else:
                continue

    try:
        # 3. 최근 글 파싱
        if request.args.get("stage") is None:
            if xsb.target == 'naver':
                recent = xsb.recent_post(target='tistory')
                return render_template("recent_articles.html", posts=recent)
            elif xsb.target == 'tistory':
                recent = xsb.recent_post(target='naver')
                return render_template("recent_articles.html", posts=recent)
            else:
                # 2. 어디로 글을 옮길건지 선택
                if xsb.target is None and request.args.get('target') is None:
                    return render_template('select_target.html')
                elif xsb.target is None and request.args.get('target') is not None:
                    xsb.target = request.args.get('target')
                    clients[session['xsb']] = xsb.__dict__
                    return redirect(url_for('main'))

        # 4. 선택된 글 다운로드
        elif request.args.get("stage") == "4":
            selected_posts = request.form.getlist('selection[]')
            xsb.target_posts = selected_posts
            download_result = xsb.download_post(selected_posts)
            clients[session['xsb']] = xsb.__dict__
            return render_template("confirm_upload.html", posts=download_result,
                                   blog={'source': '티스토리' if xsb.target == 'naver' else '네이버',
                                         'target': '티스토리' if xsb.target == 'tistory' else '네이버'})
        # 5. 글 업로드
        elif request.args.get("stage") == "5":
            results = xsb.upload_post()
            return "성공"

        else:
            raise XSBError("잘못된 접근입니다.")

    except XSBError as e:
        # 오류 발생시 오브젝트 삭제
        del session['xsb']
        del session['tistory_name']
        del session['naver_name']
        del session['tistory_token']
        del session['naver_token']
        del xsb
        del clients[session['xsb']]

        return e.message


@app.route('/login', methods=['GET'])
def login_requests():
    from flask import request, redirect
    import requests
    import keys

    if request.args.get("target") is None or request.args.get("blogName") is None:
        return "잘못된 접근입니다."

    if request.args.get("target") == "naver":
        url = "https://nid.naver.com/oauth2.0/authorize"
        param = {'client_id': keys.naver_app_id, 'redirect_uri': keys.naver_callback_uri, 'response_type': 'code',
                 'state': request.args.get("blogName")}
        return redirect(requests.get(url, params=param).url, code=302)
    elif request.args.get("target") == "tistory":
        url = "https://www.tistory.com/oauth/authorize"
        param = {'client_id': keys.tistory_app_id, 'redirect_uri': keys.tistory_callback_uri, 'response_type': 'code',
                 'state': request.args.get("blogName")}
        return redirect(requests.get(url, params=param).url, code=302)
    else:
        return "잘못된 접근입니다."


@app.route('/tistory_auth_code', methods=['GET'])
def tistory_access_token():
    import keys
    import requests
    from urllib import parse
    from flask import redirect, url_for, request, session

    try:
        url = "https://www.tistory.com/oauth/access_token"
        param = {'client_id': keys.tistory_app_id, 'redirect_uri': keys.tistory_callback_uri,
                 'grant_type': 'authorization_code', 'client_secret': keys.tistory_secret,
                 'code': request.args.get('code')}
        r = requests.get(url, params=param)
        if r.text.count("invalid_request") is not 0:
            raise IndexError

        token = r.text.split('=')[1]
        blog_name = parse.urlparse(request.args.get('state'))[2]

        session['tistory_token'] = token
        session['tistory_name'] = blog_name
        return redirect(url_for('main'))

    except (IndexError, ValueError):
        return "로그인 실패"


@app.route('/naver_auth_code', methods=['GET'])
def naver_access_token():
    import keys
    import requests
    import json
    from urllib import parse
    from flask import redirect, url_for, request, session

    try:
        url = "	https://nid.naver.com/oauth2.0/token"
        param = {'client_id': keys.naver_app_id, 'redirect_uri': keys.naver_callback_uri,
                 'grant_type': 'authorization_code', 'client_secret': keys.naver_secret,
                 'code': request.args.get('code'), 'state': request.args.get('state')}
        r = json.loads(requests.get(url, params=param).text)

        session['naver_name'] = parse.urlparse(request.args.get('state'))[2]
        session['naver_token'] = r['access_token']

        return redirect(url_for('main'))
    except KeyError:
        return "로그인 실패"


####  개발용  ####
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=12321, debug=True)
