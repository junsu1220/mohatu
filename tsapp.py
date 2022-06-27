from flask import Flask, render_template, request, jsonify, make_response
from pymongo import MongoClient
import datetime
import bcrypt, jwt
from functools import wraps




client = MongoClient('mongodb+srv://taesikyoon97:louis17467@cluster0.ncjxm.mongodb.net/Cluster0?retryWrites=true&w=majority')
db = client.dbsparta



app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
# 암호화에 넣을 시크릿 키 ( 아래 두개의 차이점은 무엇일까,,,)
SECRET_KEY = 'hello'
# app.config['SECRET_KEY'] = 'hello'

def token_required(f):
    @wraps(f)
    def decorated(*args,**kwargs):
        token = request.args.get('token')
        if not token:
            return jsonify({"message": 'Token is missing'}),403
        try:
            data = jwt.decode(token,app.config['SECRET_KEY'])
        except:
            return jsonify({"message": 'Token is invaild'}),403

        return f()(*args,**kwargs) # 이게뭐지?... 이걸 이해를 못해서 응용해서 사용해보고싶은데 뭔지 모르니 사용불가..
                                   # 응용하고싶은건 홈페이지에 접속해서 토큰이 존재하면 회원으로 메인화면 뜨게하기
                                   # 로그인 된 상태가 아니라면 로그인 화면으로 랜더링해주기
    return decorated

# def token_required_test(f):
#     @wraps(f)
#     def decorated_test(*args,**kwargs):
#         token = request.args.get('token')
#         if not token:
#             return jsonify({"message": '로그인이  필요합니다.'}),403
#         try:
#             data = jwt.decode(token,app.config['SECRET_KEY'])
#             return render_template('index.html',username=token['id'])
#         except:
#             return jsonify({"message": '토큰이 유효하지 않습니다'}),403
#
#         # return f()(*args,**kwargs)
#     return decorated_test
# 메인화면
@app.route("/")
@token_required
def index():
    return render_template('index.html')
#만약 로그인이 된 상태라면 굳이 바로 로그인 페이지를 랜더링 할 필요가 없지않나

# 로그인 화면
@app.route("/login", methods=['POST'])
def login():
    if request.method == ["POST"]:
        user_id =request.form['id_give']
        user_pw = request.form['pw_give']

        db_user = db.test.find_one({'id': user_id},{'_id':False})
        retult_pw =bcrypt.checkpw(user_pw.encode("utf-8"), db_user['pw'])


    if user_id == db_user['id'] and retult_pw == True:
        payload = {
            'id': db_user['id'],
            'exp': datetime.utcnow() + datetime.timedelta(minutes=3)  # 로그인 3분 유지
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')


        return jsonify({'result': 'success', 'access_token': token})
    else:
        return jsonify({'result': 'fail'})


# 회원가입
@app.route("/sign_up", methods=['POST'])
def sign_up():
    id_member = request.form['member_id_give']
    pw_member = request.form['member_pw_give']
    encrypted_password = bcrypt.hashpw(pw_member.encode("utf-8"), bcrypt.gensalt())
    doc = {
        'id': id_member,
        'pw': pw_member
    }
    db.members.insert_one(doc)
    return jsonify({'result': 'success'})
# 여기의 가정은 유효성 검사도 login.index에서 해주니 저희 서버가 받는 값은 거르고 걸러져서 회원가입이 가능한 상태의 id, pw 가 온다는 가정

# 중복확인 버튼 입력 >>> 서버 코드
@app.route('/check_up',methods=['POST'])
def check_same_id():
    if request.method == 'POST':
        try:
            db_user = db.test.find_one({'id': request.form["id_give"]})['id']
        except: return jsonify({"message":"중복이아닙니다"})
        else: return jsonify({"message":"중복입니다"})

@app.route('/logout')
def logout():
    pass




if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)
