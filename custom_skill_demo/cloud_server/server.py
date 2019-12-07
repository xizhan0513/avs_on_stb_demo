import json
from furl import furl
from datetime import datetime, timedelta

from flask import Flask
from flask import session, request
from flask import render_template, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import gen_salt
from flask_restful import Api, Resource, fields, marshal_with

import paho.mqtt.client as mqtt

MQTT_SERVER_IP      = "54.250.71.242"
MQTT_SERVER_PORT    = 1883


# 创建flask实例
app = Flask(__name__, template_folder='templates')
app.debug = True
app.secret_key = 'secret'
app.config.update({
    'SQLALCHEMY_DATABASE_URI': 'sqlite:///db.sqlite',
})


# 创建数据库ORM
db = SQLAlchemy(app)


# 存储oauth认证服务器用户信息的ORM
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    clientname = db.Column(db.String(40), unique=True)


# 存储资源服务器用户名、密码、设备信息
class Resources(db.Model):
    __tablename__ = 'Resources'
    username = db.Column(db.String(20), primary_key=True)
    password = db.Column(db.String(20))
    dev_id   = db.Column(db.String(100))
    stb_num  = db.Column(db.String(100))


# 存储oauth客户端信息的ORM
class Client(db.Model):
    client_id = db.Column(db.String(40), primary_key=True)
    client_secret = db.Column(db.String(55), nullable=False)

    user_id = db.Column(db.ForeignKey('user.id'))
    user = db.relationship('User')

    _redirect_uris = db.Column(db.Text)
    _default_scopes = db.Column(db.Text)

    @property
    def client_type(self):
        return 'public'

    @property
    def redirect_uris(self):
        if self._redirect_uris:
            return self._redirect_uris.split()
        return []

    @property
    def default_redirect_uri(self):
        return self.redirect_uris[0]

    @property
    def default_scopes(self):
        if self._default_scopes:
            return self._default_scopes.split()
        return []


# 存储授权码信息的ORM
class Grant(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE')
    )
    user = db.relationship('User')

    client_id = db.Column(
        db.String(40), db.ForeignKey('client.client_id'),
        nullable=False,
    )
    client = db.relationship('Client')

    code = db.Column(db.String(255), index=True, nullable=False)

    redirect_uri = db.Column(db.String(255))
    expires = db.Column(db.DateTime)

    _scopes = db.Column(db.Text)

    resources_username = db.Column(
        db.String(20), db.ForeignKey('Resources.username'),
        nullable=False,
    )

    def delete(self):
        db.session.delete(self)
        db.session.commit()
        return self

    @property
    def scopes(self):
        if self._scopes:
            return self._scopes.split()
        return []


# 存储token信息的ORM
class Token(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(
        db.String(40), db.ForeignKey('client.client_id'),
        nullable=False,
    )
    client = db.relationship('Client')

    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id')
    )
    user = db.relationship('User')

    # currently only bearer is supported
    token_type = db.Column(db.String(40))

    access_token = db.Column(db.String(255), unique=True)
    refresh_token = db.Column(db.String(255), unique=True)
    expires = db.Column(db.DateTime)
    _scopes = db.Column(db.Text)

    resources_username = db.Column(
        db.String(20), db.ForeignKey('Resources.username'),
        nullable=False,
    )

    @property
    def scopes(self):
        if self._scopes:
            return self._scopes.split()
        return []


def current_user():
    if 'id' in session:
        uid = session['id']
        return User.query.get(uid)
    return None


# 注册客户端用户
@app.route('/', methods=('GET', 'POST'))
def home():
    if request.method == 'POST':
        clientname = request.form.get('clientname')
        user = User.query.filter_by(clientname=clientname).first()
        if not user:
            user = User(clientname=clientname)
            db.session.add(user)
            db.session.commit()
        session['id'] = user.id
        return redirect('/client')
    user = current_user()
    return render_template('home.html', user=user)


# 登录界面
@app.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'GET':
        args = {}
        args['client_id']     = request.args.get('client_id')
        args['scope']         = request.args.get('scope')
        args['state']         = request.args.get('state')
        args['response_type'] = request.args.get('response_type')
        args['redirect_uri']  = request.args.get('redirect_uri')
        return render_template('login.html', **args)
    if request.method == 'POST':
        res_user = Resources.query.filter_by(username=request.form.get('username')).first()
        if not res_user:
            payload = {
                'status': 'Check no such user!'
            }
            return json.dumps(payload)
        if res_user.password != request.form.get('password'):
            payload = {
                'status': 'password error!'
            }
            return json.dumps(payload)

        url = '/oauth/authorize'
        params = {
            'client_id': request.form.get('client_id'),
            'scope': request.form.get('scope'),
            'response_type': request.form.get('response_type'),
            'redirect_uri': request.form.get('redirect_uri'),
            'state': request.form.get('state'),
        }
        url = furl(url).set(params)
        session['login'] = True
        session['login_user'] = res_user.username
        return redirect(url, 302)


# 注册一个新的oauth客户端
@app.route('/client')
def client():
    user = current_user()

    if not user:
        return redirect('/')

    item = Client(
        client_id=gen_salt(40),
        client_secret=gen_salt(50),
        _redirect_uris=' '.join([
            'https://pitangui.amazon.com/api/skill/link/M1YD9F7ZN5PH0C',
            ]),
        _default_scopes='email',
        user_id=user.id,
    )
    db.session.add(item)
    db.session.commit()

    return jsonify(
        client_id=item.client_id,
        client_secret=item.client_secret,
    )


def load_client(client_id):
    return Client.query.filter_by(client_id=client_id).first()


def load_grant(client_id, code):
    return Grant.query.filter_by(client_id=client_id, code=code).first()


def save_grant(args_client_id, args_code, args_redirect_uri, args_scopes):
    # decide the expires time yourself
    expires = datetime.utcnow() + timedelta(seconds=600)
    grant = Grant(
        client_id    = args_client_id,
        code         = args_code,
        redirect_uri = args_redirect_uri,
        _scopes      = ''.join(args_scopes),
        user         = current_user(),
        expires      = expires,
        resources_username     = session['login_user']
    )
    db.session.add(grant)
    db.session.commit()


def load_token(access_token=None, refresh_token=None):
    if access_token:
        return Token.query.filter_by(access_token=access_token).first()
    elif refresh_token:
        return Token.query.filter_by(refresh_token=refresh_token).first()


def save_token(args_access_token, args_refresh_token, args_token_type, args_client, username):
    toks = Token.query.filter_by(
        client_id = args_client.client_id,
        user_id   = args_client.user_id
    )
    # make sure that every client has only one token connected to a user
    for t in toks:
        db.session.delete(t)

    expires = datetime.utcnow() + timedelta(seconds=24*60*60)

    tok = Token(
        access_token  = args_access_token,
        refresh_token = args_refresh_token,
        token_type    = args_token_type,
        _scopes       = args_client._default_scopes,
        expires       = expires,
        client_id     = args_client.client_id,
        user_id       = args_client.user_id,
        resources_username  = username
    )
    db.session.add(tok)
    db.session.commit()


# Access Token URI
@app.route('/oauth/token', methods=['GET', 'POST'])
def access_token():
    if request.method == 'POST':
        data = request.form.to_dict()
        client        = load_client(data['client_id'])
        if client == None:
            payload = {
                'status': 'Client account is NULL!'
            }
            return json.dumps(payload)

        grant = load_grant(data['client_id'], data['code'])

        if grant == None:
            payload = {
                'status': 'code error!'
            }
            return json.dumps(payload)

        access_token  = gen_salt(255)
        refresh_token = gen_salt(255)
        token_type    = 'Bearer'
        username      = grant.resources_username
        save_token(access_token, refresh_token, token_type, client, username)

        payload = {
            'access_token': access_token,
            'refresh_token': refresh_token,
        }

        return json.dumps(payload)


# Authorization URI
@app.route('/oauth/authorize', methods=['GET', 'POST'])
def authorize():
    print("------------##----------------")
    if request.method == 'GET':
        if 'login' in session and session['login'] == True:
            session['login'] == False
        else:
            url = '/login'
            params = {
                'client_id': request.args.get('client_id'),
                'scope': request.args.get('scope'),
                'response_type': request.args.get('response_type'),
                'redirect_uri': request.args.get('redirect_uri'),
                'state': request.args.get('state'),
            }
            url = furl(url).set(params)
            return redirect(url, 302)

    if request.method == 'GET':
        args = {}
        client_id = request.args.get('client_id')
        client = Client.query.filter_by(client_id=client_id).first()
        if client == None:
            params = {
                'status': 'Client account is NULL!'
            }
            url = furl(request.args.get('redirect_uri')).set(params)
            return redirect(url, 302)

        args['client']       = client
        args['user']         = User.query.filter_by(id=client.user_id).first()
        args['scopes']       = request.args.get('scope')
        args['redirect_uri'] = request.args.get('redirect_uri')
        args['state']        = request.args.get('state')
        return render_template('authorize.html', **args)

    confirm = request.form.get('confirm', 'no')
    if confirm == 'yes':
        client_id    = request.form.get('client_id')
        code         = gen_salt(255)
        redirect_uri = request.form.get('redirect_uri')
        scopes       = request.form.get('scope')
        state        = request.form.get('state')
        save_grant(client_id, code, redirect_uri, scopes)

        params = {
            'code': code,
            'state': state
        }
        url = furl(redirect_uri).set(params)
        return redirect(url, 302)

    elif confirm == 'no':
        return 'User refuses authorization!'


# 资源服务器
@app.route('/api')
def api_me():
    if request.method == 'GET':
        access_token = request.args.get('access_token')
        token = load_token(access_token)

        if token:
            res_user = Resources.query.filter_by(username=token.resources_username).first()
            if res_user:
                lambda_dev_id = request.args.get('dev_id')
                user_dev_id = res_user.dev_id
                user_dev_id = user_dev_id.split(',')
                if lambda_dev_id in user_dev_id:
                    stb_num = res_user.stb_num
                    stb_num = stb_num.split(',')[int(lambda_dev_id) - 1]
                    msg = request.args.get('intent')
                    if 'value' in request.args:
                        msg += request.args.get('value')

                    client = mqtt.Client()
                    client.connect(MQTT_SERVER_IP, MQTT_SERVER_PORT, 60)
                    client.publish(stb_num, msg, 1)
                    client.disconnect()
                else:
                    print('user ' + res_user.username + ': No such device!')
            else:
                print('Denied access, token is incorrect!')
        else:
            print('Denied access, token is incorrect!')
    else:
        print('http method must be GET!')

    return 'api end'


if __name__ == '__main__':
    import os
    db.create_all()
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = 'true'
    app.run(host='0.0.0.0', port=5000)

