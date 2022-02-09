from tkinter import E
from flask import Flask, redirect, render_template, jsonify, make_response, request
import requests
import sys
import jwt
from functools import wraps

app = Flask(__name__)


app.config['SECRET_KEY'] = 's3cret'

def get_balance(user):
    resp = requests.post(
            'http://accounts-node:2139/get-balance',
            json={"user": user})
    return resp.json()["balance"]

def get_username(request):
    token = request.cookies.get('auth_token')
    data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
    return data["user"]

def check_daily(name):
    requests.post(
            'http://accounts-node:2139/daily',
            json={"user": name})


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.cookies.get('auth_token')
        if not token:
            return redirect('/login')
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            check_daily(data["user"])
        except:
            return 'Invalid token'
        return f(*args, **kwargs)
    return decorated

def token_prohibited(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.cookies.get('auth_token')
        if not token:
            return f(*args, **kwargs)
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
        except:
            return f(*args, **kwargs)
        return redirect('/')
    return decorated


@app.route('/')
@token_required
def root():
    return redirect('/tables')

@app.route('/friends')
@token_required
def friends():
    user = get_username(request)
    balance = get_balance(user)
    response = requests.post(
            'http://relations-node:2138/friendscontent',
            json={"username": get_username(request)})
    friends=response.json()["friends"]
    invites=response.json()["invites"]
    return render_template('friends.html', friends=friends, invites=invites, act="friends", bal=balance, usr=user)

@app.route('/api/accept', methods=['POST'])
@token_required
def api_accept():
    print('Here at least', file=sys.stderr)
    print('at:', request.json["auth_token"], file=sys.stderr)
    response = requests.post(
            'http://relations-node:2138/accept',
            json=request.json
    )
    return make_response("OK", 200)

@app.route('/api/transfer', methods=['POST'])
@token_required
def api_transfer():
    response = requests.post(
            'http://accounts-node:2139/transfer',
            json=request.json
    )
    return response

@app.route('/api/decline', methods=['POST'])
@token_required
def api_decline():
    requests.post(
            'http://relations-node:2138/decline',
            json=request.json)
    return make_response("OK", 200)


@app.route('/api/unfriend', methods=['POST'])
@token_required
def api_unfriend():
    requests.post(
            'http://relations-node:2138/unfriend',
            json=request.json)
    return make_response("OK", 200)

@app.route('/api/invite', methods=['POST'])
@token_required
def api_invite():
    requests.post(
            'http://relations-node:2138/invite',
            json=request.json)
    return make_response("OK", 200)



@app.route('/login', methods=['POST', 'GET'])
@token_prohibited
def login():
    if request.method == 'GET':
        return render_template('login.html')
    elif request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        response = requests.post(
            'http://users-node:6969/login',
            json={'password': password, 'username': username}
        )
    if response.status_code == 200:
        resp = make_response(redirect('/'))
        resp.set_cookie('auth_token', response.json()['token'])
        return resp
    return render_template('login.html', fail_info="Invalid data")


@app.route('/register', methods=['POST', 'GET'])
@token_prohibited
def register():
    if request.method == 'GET':
        return render_template('register.html')
    elif request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        response = requests.post(
            'http://users-node:6969/register',
            json={'password': password, 'username': username}
        )
        resp = requests.post(
            'http://accounts-node:2139/create-account',
            json={'user': username})
        print('Account creation: ', resp, file=sys.stderr)
    if response.status_code == 200:
        return render_template('register.html', succ_info="Account created")
    else:
        return render_template('register.html', fail_info="Username not available")


@app.route('/logout')
@token_required
def logout():
    resp = make_response((redirect('/login')))
    resp.set_cookie('auth_token', '')
    return resp

@app.route('/history')
@token_required
def match_history():
    user = get_username(request)
    balance = get_balance(user)
    return render_template('history.html', act="history", bal=balance, usr=user)

@app.route('/tables')
@token_required
def tables():
    user = get_username(request)
    balance = get_balance(user)
    return render_template('tables.html', act="tables", bal=balance, usr=user)

def get_transactions(user):
    response = requests.post(
            'http://accounts-node:2139/get-transactions',
            json={"user": user}
        )
    return response.json()

@app.route('/transactions')
@token_required
def transactions():
    user = get_username(request)
    balance = get_balance(user)
    transactions = get_transactions(user)
    transactions=[x["desc"] for x in transactions]
    return render_template('transactions.html', act="transactions", bal=balance, usr=user, tr=transactions)




if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=2137)