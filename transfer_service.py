from flask import Flask, request, render_template, redirect
from pymongo import Connection
from bson.objectid import ObjectId

import os
from datetime import datetime
from json import dumps
from urllib2 import urlopen
from hashlib import md5

app = Flask(__name__)
MONGO_HOST = os.environ.get("MONGOLAB_URI")
#MONGO_HOST = os.environ.get("MONGO_HOST")
DB = os.environ.get("MONGO_DB", "file_transfer")
connection = Connection(host=MONGO_HOST)
CONFIG_FILE = "./config.json"
DEFAULT_PORT = 13462
config = {}

def get_collection(name):
    db = connection[DB]
    return db[name]

@app.route("/")
def welcome():
    return "Welcome! (TODO: make this page)"

@app.route("/ping/<install_id>")
def ping(install_id):
    message = { '_id': ObjectId(install_id), 
                'last_seen': datetime.utcnow(),
                'remote_host': request.remote_addr,
               }
    coll = get_collection('installs')
    coll.update({'_id': message['_id']}, message, False)
    return "OK"

def get_download_uri():
    return "huuuf"

@app.route("/download/<transfer_id>")
def transfer_page(transfer_id):
    coll = get_collection('transfers')
    transfer = coll.find_one({'_id': ObjectId(transfer_id)})
    coll = get_collection('installs')
    install = coll.find_one({'_id': transfer['install_id']})
    return redirect(get_download_uri(transfer, install))

@app.route("/download/<transfer_id>/confirm/<install_id>")
def confirm_transfer(transfer_id, install_id):
    coll = get_collection('transfers')
    transfer = coll.find_one({'_id': ObjectId(transfer_id)})
    if transfer['install_id'] != install_id:
        return dumps({'error': 'Not authorized'})
    if transfer:
        return dumps(transfer)
    else:
        return dumps({'error': 'Transfer not found'})

#@app.route("/app/<install_id>/list")
#def list_files(install_id):
#    coll = get_collection('installs')
#    install = coll.find_one({'_id': transfer['install_id']})
#    return redirect(get_list_uri(install))

def get_user(username):
    # TODO: Check authentication for this first
    coll = get_collection('users')
    user = coll.find_one({'username': username})
    return user
    
def logged_in_user():
    coll = get_collection('users')
    user = coll.find_one({'user_token': request.form['user_token']})
    return user

@app.route("/app/register", methods=["POST"])
def register_install():
    # TODO: Validate input
    user = logged_in_user()
    if not user:
        return dumps({'error': "Unable to login"})
    coll = get_collection('installs')
    message = { '_id': ObjectId(), 
                'last_seen': datetime.utcnow(),
                'remote_host': request.remote_addr,
                'remote_port': request.form['port'],
                'user_id': user['_id']
               }
    coll.insert(message)
    return dumps({'install_id': message['_id']})

#def get_list_uri(install):
#    return "http://%s:%s/list" % (install['remote_host'], 
#                                      install['remote_port'],
#                                      transfer['path'])

def get_transfer_status(transfer):
    pass

def test_install_accessible(install):
    try:
        response = urlopen("http://%s:%s/pong"  % 
                           (install['remote_host'], install['remote_port']))
        status = response.read()
        if status['status'] == 'OK':
            return True
    except:
        return False
    return False
        
        
@app.route("/user/login", methods=["POST"])
def login():
    coll = get_collection('users')
    # TODO: escape items sent to DB
    user = coll.find_one({'username': request.form.get('username'),
                          'password': request.form.get('password')})
    if user:
        return dumps({'user_token': user['token']})        
    return dumps({'error': "User not found"})

def user_token(username, password):
    d = md5()
    d.update(username + password + "MEH")
    return d.digest()

@app.route("/user/new", methods=["POST"])
def new_user():
    coll = get_collection('users')
    # TODO: Escape items sent to DB
    user = coll.find_one({'username': request.form['username']})
    if user:
        return dumps({"error": "Username already taken"})
    # TODO: Verify form parameters
    username = request.form.get('username')
    password = request.form.get('password')
    if username and password:
        user = {'username': username,
                'password': password,
                'token': user_token(username, password)
                }
        coll.insert(user)
    else:
        return "Unable to create user"
    return dumps({'user_token': user['token']}) 
    
@app.route("/status/<transfer_id>")
def status(transfer_id):
    coll = get_collection('transfers')
    transfer = coll.find_one({'_id': ObjectId(transfer_id)})
    if not transfer.get('status'):
        status = get_transfer_status(transfer)
        transfer['status'] = status
    return dumps(transfer or {})

@app.route("/transfer/<install_id>/<path:path>")
def create_transfer(install_id, path):
    coll = get_collection('installs')
    install = coll.find_one({'id': install_id})
    if not install:
        return {'error': 'Unable to find install'}
    transfer_id = ObjectId()
    transfer = {'_id': transfer_id, 'path': path, 'install_id': install_id}
    coll.insert(transfer)
    return dumps(transfer)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", DEFAULT_PORT))
    print port
    app.run(host='0.0.0.0', port=port)
