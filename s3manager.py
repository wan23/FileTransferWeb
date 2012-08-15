import os
from boto.s3.connection import S3Connection
from boto.s3.key import Key
from boto.s3.bucket import Bucket

# TODO: Delete the defaults for the keys!
ACCESS_KEY = os.environ.get("AWS_ACCESS_KEY_ID", "0T9CREAFWT4RCXPN5Q82")
SECRET_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY", "UTAYEzebJClKn7jAg9+E8nMCe+nngzYcJxmwRJqG")
BUCKET = os.environ.get("AWS_BUCKET", 'juanwalker.com.filesendtest')

class S3Manager:
  def __init__(self):
    # Use environment vars AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY
    self.conn = S3Connection(ACCESS_KEY, SECRET_KEY)
    self.bucket = Bucket(self.conn, BUCKET)

  def get_key(self, install_id, file_hash):
    return Key(self.bucket, "%s/%s" % (install_id, file_hash))

  def get_upload_url(self, transfer, expires):
    print transfer
    k = self.get_key(str(transfer['install_id']), transfer['file_hash'])
    headers = None
    if transfer['file']['mime_type']:
    	headers = {'Content-Type':  transfer['file']['mime_type']}
    	print headers
    return k.generate_url(expires, method='PUT', headers=headers)

  def get_download_url(self, install_id, file_hash, expires):
    k = self.get_key(install_id, file_hash)
    return k.generate_url(expires, method='GET')

