from flask import Flask, request, redirect
from pymongo import Connection
from bson.objectid import ObjectId
from s3manager import S3Manager

import os
from datetime import datetime
from json import dumps, loads
from urllib2 import urlopen
from hashlib import md5

from emailsender import send_file_received_email

app = Flask(__name__)

MONGO_HOST = os.environ.get("MONGOLAB_URI")
DB = os.environ.get("MONGO_DB", "file_transfer")
connection = Connection(host=MONGO_HOST)
CONFIG_FILE = "./config.json"
DEFAULT_PORT = 13463
UPLOAD_TIME_LIMIT = 60 * 60 * 24
DOWNLOAD_TIME_LIMIT = 60 * 60 * 24
S3_MANAGER = S3Manager()


def get_collection(name):
    db = connection[DB]
    return db[name]

    
def update_last_seen(install_id, remote_host):
    install = get_install(install_id)
    install.update({'last_seen': datetime.utcnow(),
	                'remote_host': remote_host,
	                'user_id': logged_in_user()['_id']})
    coll = get_collection('installs')
    coll.save(install)

@app.route("/ping/<install_id>", methods=["POST"])
def ping(install_id):
    update_last_seen(install_id, request.remote_addr)
    transfers = get_transfers_for_install(install_id)
    ret = {'status': "OK"}
    
    if transfers:
    	files = [{'transfer_id': str(t['_id']), 'file_hash': t['file_hash']} 
    	         for t in transfers]
    	ret.update({'command': 'get_file', 'transfers': files})
    else:
    	ret.update({'command': 'test'})
    	
    return dumps(ret)
    
def get_transfers_for_install(install_id):
	coll = get_collection('transfers')
	transfers = list(coll.find({'install_id': ObjectId(install_id), 'status': 'new'}))
	return transfers

def get_download_uri(user_id, file_hash):
    #TODO: The time the url lasts for should be based on the user somehow
    return S3_MANAGER.get_download_url(user_id, file_hash, 24 * 60 * 60)
    
def get_install(install_id):
    coll = get_collection('installs')
    return coll.find_one({'_id': ObjectId(install_id)})
    
def get_transfer(transfer_id):
	coll = get_collection('transfers')
	return coll.find_one({'_id': ObjectId(transfer_id)})

def get_user_by_name(username):
    # TODO: Check authentication for this first
    coll = get_collection('users')
    user = coll.find_one({'username': username})
    return user

def get_user(user_id):
    coll = get_collection('users')
    return coll.find_one({'_id': ObjectId(user_id)})

def logged_in_user():
    coll = get_collection('users')
    user = coll.find_one({'token': request.form['user_token']})
    return user

def error_response(error_text):
    return dumps({'status': 'error', 'error': error_text))

def ok_response(data={}):
    response = {'status': 'OK'}
    response.update(data)
    return dumps(response)

@app.route("/install/register", methods=["POST"])
def register_install():
    # TODO: Validate input
    user = logged_in_user()
    if not user:
        return dumps({'error': "Unable to login"})
    coll = get_collection('installs')
    install_id = ObjectId()
    message = { '_id': install_id, 
                'last_seen': datetime.utcnow(),
                'remote_host': request.remote_addr,
                'remote_port': request.form['port'],
                'user_id': user['_id'],
                'file_collection': 'files_' + str(install_id)
               }
    coll.insert(message)
    return dumps({'install_id': str(message['_id'])})

@app.route("/install/<install_id>/files", methods=["POST"])
def handle_file_list(install_id):
    # TODO: Validate input
    user = logged_in_user()
    if not user:
        return error_response("Need to login")
    
    listing = loads(request.form['file_list'])
    install = get_install(install_id)
    install['file_listing'] = listing['files']
       
    coll = get_collection('installs')
    coll.save(install)
    return dumps({'status': 'OK'})

@app.route("/install/<install_id>/files", methods=["GET"])
def get_file_list(install_id):
	# TODO: verify auth
	install = get_install(install_id)
	if not install:
		return dumps({'status': 'Error', 'error': 'Install not found'})
	listing = install.get('file_listing', [])
	return dumps({'status': 'OK', 'files': listing})
	
	
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
def login_user():
    # TODO: Verify form parameters
    username = request.form.get('username')
    password = request.form.get('password')
    return login(username, password)

def login():
    coll = get_collection('users')
    # TODO: escape items sent to DB
    user = coll.find_one({'username': username,
                          'password': password})
    if user:
        return dumps({'user_token': user['token']})        
    return dumps({'error': "User not found"})

def user_token(username, password):
    d = md5()
    d.update(username)
    d.update(password)
    d.update("MEH")
    return d.hexdigest()

@app.route("/user/new", methods=["POST"])
def new_user():
    # TODO: Verify form parameters
    username = request.form.get('username')
    password = request.form.get('password')
    return create_user(username, password)
    
def create_user(username, password):
    coll = get_collection('users')
    # TODO: Escape items sent to DB
    user = coll.find_one({'username': request.form.get('username')})
    if user:
        return dumps({"error": "Username already taken"})

    if username and password:
        user = {'username': username,
                'password': password,
                'token': user_token(username, password)
                }
        coll.insert(user)
    else:
        return "Unable to create user"
    return dumps({'user_token': user['token']}) 
    
@app.route("/transfer/<transfer_id>/status")
def status(transfer_id):
    coll = get_collection('transfers')
    transfer = coll.find_one({'_id': ObjectId(transfer_id)})
    if not transfer.get('status'):
        status = get_transfer_status(transfer)
        transfer['status'] = status
    return dumps(transfer or {})
    
@app.route("/transfer/<transfer_id>/start_upload", methods=['POST'])
def start_upload(transfer_id):
	# TODO: Should require auth
    coll = get_collection('transfers')
    transfer = coll.find_one({'_id': ObjectId(transfer_id)})
    transfer['status'] = 'uploading'
    coll.save(transfer)
    url = S3_MANAGER.get_upload_url(transfer, UPLOAD_TIME_LIMIT)
    return dumps({'status': 'OK', 'url': url})


@app.route("/transfer/new", methods=['POST'])
def create_transfer():
    user = logged_in_user()
    install_id = request.form.get('install_id')
    file_hash = request.form.get('file_hash')
    recipient_email = request.form.get('recipient_email')
    recipient_name = request.form.get('recipient_name')
    print user
    coll = get_collection('installs')
    print coll
    install = coll.find_one({'_id': ObjectId(install_id)})
    #print dict((k, v) for k, v in install.iteritems() if k != 'file_listing')
    #print install
    if not install: # or user['_id'] != install['user_id']:
    	print str(user['_id']) + '!=' + str(install['user_id'])
        return dumps({'error': 'Unable to find install'})
    # TODO: Find a better way to do this
    file = [f for f in install['file_listing'] if f['hash'] == file_hash]
    if file:
    	file = file[0]
   # print install
    transfer_id = ObjectId()
    transfer = {'_id': transfer_id, 'file_hash': file_hash,
    		    'install_id': ObjectId(install_id),
    	        'created': datetime.utcnow(), 'status': 'new', 
    	        'user_id': install.get('user_id'),
    	        'file': file,
    	        'recipient_email': recipient_email,
    	        'recipient_name': recipient_name,
    	       }
    print transfer
    coll = get_collection('transfers')
    coll.insert(transfer)
    return dumps({'status': 'OK', 'transfer_id': str(transfer_id)})


@app.route("/transfer/<transfer_id>/done", methods=['POST'])
def transfer_done(transfer_id):
    # TODO: Should require auth
    transfer = get_transfer(transfer_id)
    user = get_user(transfer['user_id'])
    transfer = get_transfer(transfer_id)
    transfer['status'] = 'upload_complete'
    coll = get_collection('transfers')
    coll.save(transfer)
    
    download_url = S3_MANAGER.get_download_url(transfer, DOWNLOAD_TIME_LIMIT)
    send_file_received_email(user, transfer, download_url, '24 Hours')
    return dumps({'status': 'OK'})


@app.route("/transfer/<transfer_id>/download")
def transfer_page(transfer_id):
    transfer = get_transfer(transfer_id)
    if transfer:
        return redirect(S3_MANAGER.get_download_url(transfer, DOWNLOAD_TIME_LIMIT))
    else:
        return dumps({'status': 'error', 'error': 'Transfer not found'})

#########################################################
# App routes 
# TODO: move to another file
from jinja2 import Environment, PackageLoader
env = Environment(loader=PackageLoader('transfer_service', './templates'))

from flask import session

home_page_template = env.get_template('home_page.html')
send_file_template = env.get_template('send_file_template.html')

@app.route("/")
def home_page():
    return home_page_template.render()

@app.route("/login", methods=['GET'])
def login_handler():
    # TODO: Return to the page you were on after logging in
    return home_page_template.render()

@app.route("/sendfile", methods=['GET'])
def login_handler():
    return send_file_template.render()

@app.route("/login", methods=['POST'])
def login_handler():
    username = request.form.get('username')
    password = request.form.get('password')
    status = login_user(username, password)
    if status.get('user_token'):
        session['user_token'] = status['user_token']
    return ok_response()

@app.route("/register", methods=['POST'])
def login_handler():
    # TODO: Validate this stuff??
    username = request.form.get('username')
    password = request.form.get('password')
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    email = request.form.get('email')
    status = create_user(username, password, first_name, last_name, email)
    if status.get('user_token'):
        session['user_token'] = status['user_token']
        return ok_response()
    else:
        return error_response('Could not create user')



if __name__ == '__main__':
    port = int(os.environ.get("PORT", DEFAULT_PORT))
    print port
    app.debug = True
    app.run(host='0.0.0.0', port=port)
