
# XSB
Cross-Site-Blogging : 네이버와 Tistory 블로그를 연동하는 웹 애플리케이션

**기능**
 - 최근 글 표시
 - 글 다운로드 (사진 포함) 후 다른 플랫폼에 업로드 (예: 티스토리에 작성한 글을 네이버에 복사)

다른 블로그로의 이전을 원하는 블로거나, 여러 플랫폼에 동시에 기고하는 블로거를 위해 만든 프로그램입니다. 
> 제작중

# 사용방법
> 제작중

**필요사항**

 - Python 인터프리터 (3.7+)
 - Requests 모듈 `pip install requests`	
 - Flask 모듈 `pip install flask`

**환경설정**

 - config.py (변수로 설정)
	 - file_save_path = 블로그 사진들을 저장할 주소(쓰기 가능한 폴더)
  - keys.py (변수로 설정)
	  - tistory_app_id = 티스토리 api 앱 아이디
	  - tistory_secret = 티스토리 api 개인키
	  - tistory_callback_uri = 티스토리에 등록한 콜백 주소
	  - naver_app_id = 네이버 api 앱 아이디 (로그인, 블로그 글 작성 권한 필요)
	  - naver_secret = 네이버 api 개인키
	  - naver_callback_uri = 네이버에 등록한 콜백 주소

**API 등록**
> 티스토리

[https://www.tistory.com/guide/api/manage/register](https://www.tistory.com/guide/api/manage/register)에서 PC 애플리케이션으로 등록

>네이버

[https://developers.naver.com/apps/#/register](https://developers.naver.com/apps/#/register)에서 네이버 아이디로 로그인, 블로그 api 사용으로 등록


**실행**

 1. main.py 실행 -> Flask가 debug 모드로 실행됨
 2. 127.0.0.1:12321/xsb 접속 
 3. OAuth를 이용해 로그인한 후 대상 설정
 4. 최근 글 중에서 선택하고 확인
