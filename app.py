from pymongo import MongoClient
import jwt
import certifi
import datetime
import requests
from bs4 import BeautifulSoup
import hashlib
from flask import Flask, render_template, jsonify, request, redirect, url_for, Response
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from bson import ObjectId

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config['UPLOAD_FOLDER'] = "./static/profile_pics"

ca = certifi.where()

client = MongoClient('mongodb+srv://test:sparta@cluster0.6bd2d.mongodb.net/?retryWrites=true&w=majority', tlsCAFile=ca)
db = client.dbsparta

SECRET_KEY = 'SPARTA'

@app.route('/')
def main():
    token_receive = request.cookies.get('mytoken')
    countrys = list(db.countrys.find({}, {"_id": False}))

    if token_receive is not None:
        try:
            payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
            user = db.users.find_one({"user_id": payload["user_id"]}, {'_id': False})
            return render_template('index.html', countrys=countrys, id=user["user_id"])
        except jwt.ExpiredSignatureError:
            msg = '로그인 시간이 만료되었습니다.'
            return render_template('error/401.html', msg=msg), 401
        except jwt.DecodeError:
            msg = '로그인 정보가 존재하지 않습니다.'
            return render_template('error/401.html', msg=msg), 401
    else:
        return render_template('index.html', countrys=countrys)

@app.route("/info", methods=["POST"])
def main_info():
    url = 'https://www.skyscanner.co.kr/news/inspiration/top10-europe-destinations-where-koreans-love-to-go'

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36'}
    data = requests.get(url, headers=headers)

    soup = BeautifulSoup(data.text, 'html.parser')

    card_image = soup.select('#post-321 > div > div > div.entry-content > figure')
    card_title = soup.select('#post-321 > div > div > div.entry-content > h2')

    n = 0
    desc_list = []
    short_desc_list = []
    for desc in soup.select("p", class_="entry-content"):
        n = n + 1
        if (n > 2):
            desc_list.append(desc.text)
            short_desc_list.append((desc.text).split('.')[0])

    # print(desc_list)
    print(short_desc_list)

    check = list(db.countrys.find({}, {'_id': False}))
    # print(check)
    count = 0

    if len(check) == 0:
        for image, title in zip(card_image, card_title):
            count = count + 1
            image = image.select_one('img')['src']
            title = title.select_one('a').text
            # print(image, title)
            doc = {
                'post_num': count,
                'title': title,
                'image_link': image,
                'desc': desc_list[count - 1],
                'short_desc': short_desc_list[count - 1]
            }
            print(doc)

            db.countrys.insert_one(doc)

    return jsonify({'msg': 'main화면정보 저장완료'})

@app.route('/login_main')
def login_main():
    return render_template('login.html')

# 회원 가입
@app.route('/register', methods=['POST'])
def register_user():
    user_id_receive = request.form['username_give']
    pw_receive = request.form['password_give']
    pw_hash = hashlib.sha256(pw_receive.encode('utf-8')).hexdigest()
    if is_user_id_exist(user_id_receive):
        return Response(response='이미 존재하는 ID 입니다. 중복 확인을 다시 해주세요.', status=400)
    else:
        doc = {
            "user_id": user_id_receive,
            "pw": pw_hash,
        }

        db.users.insert_one(doc)
        return jsonify({'result': 'success'})

# 아이디 중복 체크
@app.route('/register/check_dup', methods=['POST'])
def check_dup():
    username_receive = request.form['username_give']
    exists = bool(db.users.find_one({"user_id": username_receive}))
    return jsonify({'result': 'success', 'exists': exists})

@app.route('/detail/<post_num>')
def detail(post_num):

    # post_num에 해당하는 국가 정보 찾음
    country = db.countrys.find_one({'post_num': int(post_num)})

    # post_num에 해당하는 comment 정보 찾음
    country_comment = list(db.comments.find({'post_num': int(post_num)}, {'_id': False}))
    # print(country_comment)
    comments = list(db.comments.find({},{'_id':False}))

    try:
        token_receive = request.cookies.get('mytoken')
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        user_info = db.users.find_one({"username": payload["user_id"]},{'_id':False})
        return render_template("detail.html", country_comment=country_comment, country=country, user_info=user_info)

    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return render_template("detail.html", country_comment=country_comment, country=country)

# 로그인
@app.route('/sign_in', methods=['POST'])
def sign_in():
    print("success")
    user_id_receive = request.form['username_give']
    pw_receive = request.form['password_give']

    pw_hash = hashlib.sha256(pw_receive.encode('utf-8')).hexdigest()
    result = db.users.find_one({'user_id': user_id_receive, 'pw': pw_hash})

    if result is not None:
        payload = {
            'user_id': user_id_receive,
            'exp': datetime.utcnow() + timedelta(seconds=60 * 60 * 24)
        }

        # token = jwt.encode(payload, SECRET_KEY, algorithm='HS256').decode('utf-8')
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')

        return jsonify({'result': 'success', 'token': token})
    else:
        return jsonify({'result': 'fail', 'msg': '아이디/비밀번호가 일치하지 않습니다.'})

@app.route('/post', methods=['POST'])
def add_post():
    token_receive = request.cookies.get('mytoken')
    print("토큰정보")
    print(token_receive)
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        user_info = db.users.find_one({"username": payload["user_id"]})
        comment_receive = request.form["comment_give"]
        post_num_receive = request.form["post_num_give"]

        doc = {
            "post_num": int(post_num_receive),
            "comment": comment_receive,
            "username": user_info["username"]
        }
        db.comments.insert_one(doc)
        return jsonify({'result': 'success', 'msg': '커멘트 저장'})
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("login"))

@app.route('/mypage')
def mypage():

    token_receive = request.cookies.get('mytoken')
    payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
    user_info = db.users.find_one({"username": payload["user_id"]},{'_id':False})

    mys = list(db.comments.find({}))

    return render_template("mypage.html", mys = mys, user_info = user_info)

def is_user_id_exist(user_id):
    return db.users.find_one({'user_id': user_id}) is not None

if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)