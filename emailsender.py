import requests

from jinja2 import Environment, PackageLoader
env = Environment(loader=PackageLoader('emailsender', './templates'))

# TODO: Change API KEY and remove from source control
MAILGUN_API_URL = 'https://api.mailgun.net/v2'
MAILGUN_API_KEY = 'key-9ymo7ck40rvrc6nmoqpamy01hjw7os10'
MAILGUN_DOMAIN = 'app5340038.mailgun.org'

file_ready_text_template = env.get_template('file_ready_email.txt')
file_ready_html_template = env.get_template('file_ready_email.html')


def _send_mail(from_name, from_address, to_address, subject, body_text, 
               body_html=None, tag=None):
    data = { 
            "from": "%s <%s>" %(from_name, from_address),
            "to": [to_address],
            "subject":subject,
            "text": body_text,
    }
    if tag:
        data["o:tag"] = tag
    if body_html:
        data["html"] = body_html
    
    r = requests.post(("%s/%s/messages" % (MAILGUN_API_URL, MAILGUN_DOMAIN)), 
                      auth=("api", MAILGUN_API_KEY),
                      data=data)
    return r
    
    
def send_file_received_email(sender_user, transfer, download_url, expiration):
    body_text = file_ready_text_template.render(sender_name=sender_user.get('name', 
                                                                            'Juan'),
                                                name=transfer['recipient_name'],
                                                file_name=transfer['file']['name'],
                                                file_url=download_url,
                                                file_expiration=expiration,
                                                )
    body_html = file_ready_html_template.render(sender_name=sender_user.get('name',
                                                                            'Juan'),
                                                name=transfer['recipient_name'],
                                                file_name=transfer['file']['name'],
                                                file_url=download_url,
                                                file_expiration=expiration,
                                                )
    _send_mail(sender_user.get('name', 'Juan'), 
               sender_user.get('email', 'smurf@juanwalker.com'),
               transfer['recipient_email'],
               'Your file has arrived',
               body_text, body_html=body_html, tag='test')
    
    