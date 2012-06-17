from flask import Flask, request, render_template
from pymongo import Connection, objectid
from pymongo.objectid import ObjectId

from datetime import datetime
from json import dumps
from urllib2 import urlopen

app = Flask(__name__)
connection = Connection()
DB = file_transfer

DEFAULT_PORT = 13462

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

@app.route("/download/<transfer_id>")
def transfer_page(transfer_id):
    coll = get_collection('transfers')
    transfer = coll.find_one({'_id': ObjectId(transfer_id)})
    coll = get_collection('installs')
    install = coll.find_one({'_id': transfer['install_id']})
    return flask.redirect(get_download_uri(transfer, install))

@app.route("/download/<transfer_id>/confirm/<install_id>"):
def confirm_transfer(transfer_id):
    coll = get_collection('transfers')
    transfer = coll.find_one({'_id': ObjectId(transfer_id)})
    if transfer['install_id'] != install_id:
        return dumps({'error': 'Not authorized'})
    if transfer:
        return dumps(transfer)
    else:
        return dumps({'error': 'Transfer not found'})
    

@app.route("/app/<install_id>/list")
def list_files(install_id):
    coll = get_collection('installs')
    install = coll.find_one({'_id': transfer['install_id']})
    return flask.redirect(get_list_uri(install))

@app.route("/app/register", methods=["POST"])
def register_install(transfer, install):
    # TODO: Validate input
    coll = get_collection('installs')
    message = { '_id': ObjectId(), 
                'last_seen': datetime.utcnow(),
                'remote_host': request.remote_addr,
                'remote_port': request.form['port'],
                'user': request.form['user_id']
               }
    coll.insert(message)
    return dumps(message)

def get_list_uri(install):
    return "http://%s:%s/list" % (install['remote_host'], 
                                      install['remote_port'],
                                      transfer['path'])

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
        
@app.route("/status/<transfer_id>")
def status(transfer_id)
    coll = get_collection('transfers')
    transfer = coll.find_one({'id': ObjectId(transfer_id)})
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
    app.run()
