#!/usr/bin/python3
#-*- coding: utf-8 -*-
""" cassh_html """

# Standard library imports
from __future__ import print_function
from base64 import urlsafe_b64decode, urlsafe_b64encode
from datetime import datetime
from functools import wraps
from json import dumps, loads
from os import getenv, path
from ssl import PROTOCOL_TLSv1_2, SSLContext

# Third party library imports
from flask import Flask, render_template, request, Response, redirect, url_for, send_from_directory
from requests import get, post, put
from requests.exceptions import ConnectionError
from urllib3 import disable_warnings
from werkzeug import secure_filename

# Disable HTTPs warnings
disable_warnings()

# Debug
# from pdb import set_trace as st

APP = Flask(__name__)
APP.config.from_pyfile('settings.txt')
# These are the extension that we are accepting to be uploaded
APP.config['ALLOWED_EXTENSIONS'] = set(['pub'])

def allowed_file(filename):
    """ For a given file, return whether it's an allowed type or not """
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in APP.config['ALLOWED_EXTENSIONS']

def check_auth_by_status(auth):
    try:
        req = get(APP.config['CASSH_URL'] + '/client' + 
            auth_url(auth.username, password=auth.password), verify=False)
    except ConnectionError:
        return Response('Connection error : %s' % APP.config['CASSH_URL'])
    # If there is no account
    if req.text == 'None':
        return True
    try:
        result = loads(req.text)
    except:
        return False
    return True

def decode(key, enc):
    dec = []
    enc = urlsafe_b64decode(enc).decode()
    for i in range(len(enc)):
        key_c = key[i % len(key)]
        dec_c = chr((256 + ord(enc[i]) - ord(key_c)) % 256)
        dec.append(dec_c)
    return "".join(dec)

def encode(key, clear):
    enc = []
    for i in range(len(clear)):
        key_c = key[i % len(key)]
        enc_c = chr((ord(clear[i]) + ord(key_c)) % 256)
        enc.append(enc_c)
    return urlsafe_b64encode("".join(enc).encode()).decode()

def requires_auth(func):
    """ Wrapper which force authentication """
    @wraps(func)
    def decorated(*args, **kwargs):
        """ Authentication wrapper """
        current_user = {}
        current_user['name'] = request.cookies.get('username')
        try:
            current_user['password'] = decode(APP.config['ENCRYPTION_KEY'], request.cookies.get('password'))
        except:
            current_user['password'] = 'Unknown'
        current_user['is_authenticated'] = request.cookies.get('last_attempt_error') == 'False'
        if current_user['name'] == 'Unknown' and current_user['password'] == 'Unknown':
            current_user['is_authenticated'] = False
        return func(current_user=current_user, *args, **kwargs)
    return decorated

def auth_url(realname, password=None, prefix=None):
    """
    Return a ?xxx=xxx to put at the end of a GET request.
    """
    if APP.config['ENABLE_LDAP']:
        if prefix is None:
            return '?realname=%s&password=%s'\
                % (realname, password)
        else:
            return prefix + '&realname=%s&password=%s'\
                % (realname, password)
    else:
        if prefix is None:
            return ''
        else:
            return prefix


@APP.route('/')
@requires_auth
def index(current_user=None):
    """ Display home page """
    return render_template('homepage.html', username=current_user['name'], \
        logged_in=current_user['is_authenticated'], \
        display_error=request.cookies.get('last_attempt_error')=='True', \
        login_banner=APP.config['LOGIN_BANNER'])

@APP.route('/login', methods=['POST'])
@requires_auth
def login(current_user=None):
    username = request.form['username']
    password = request.form['password']
    last_attempt_error = False
    redirect_to_index = redirect('/')
    response = APP.make_response(redirect_to_index)
    try:
        req = get(APP.config['CASSH_URL'] + '/test_auth' +
            auth_url(username, password=password), verify=False)
    except:
        return Response('Connection error : %s' % APP.config['CASSH_URL'])
    if 'OK' in req.text:
        response.set_cookie('username',value=username)
        response.set_cookie('password',value=encode(APP.config['ENCRYPTION_KEY'], password))
    else:
        last_attempt_error = True
    response.set_cookie('last_attempt_error',value=str(last_attempt_error))
    return response

@APP.route('/logout', methods=['POST'])
@requires_auth
def logout(current_user=None):
    redirect_to_index = redirect('/')
    response = APP.make_response(redirect_to_index)
    response.set_cookie('username',value='Unknown')
    response.set_cookie('password',value='Unknown')
    response.set_cookie('last_attempt_error',value='False')
    return response

@APP.route('/add/')
@requires_auth
def cassh_add(current_user=None):
    """ Display add key page """
    return render_template('add.html', username=current_user['name'], \
        logged_in=current_user['is_authenticated'])

@APP.route('/sign/')
@requires_auth
def cassh_sign(current_user=None):
    """ Display sign page """
    return render_template('sign.html', username=current_user['name'], \
        logged_in=current_user['is_authenticated'])

@APP.route('/status/')
@requires_auth
def cassh_status(current_user=None):
    """ Display status page """
    try:
        req = get(APP.config['CASSH_URL'] + '/client' + 
            auth_url(current_user['name'], password=current_user['password']), verify=False)
    except ConnectionError:
        return Response('Connection error : %s' % APP.config['CASSH_URL'])
    try:
        result = loads(req.text)
        is_expired = datetime.strptime(result['expiration'], '%Y-%m-%d %H:%M:%S') < datetime.now()
        if result['status'] == 'ACTIVE':
            if is_expired:
                result['status'] = 'EXPIRED'
            else:
                result['status'] = 'SIGNED'
    except:
        result = req.text

    return render_template('status.html', username=current_user['name'], result=result, \
        logged_in=current_user['is_authenticated'])

# Route that will process the file upload
@APP.route('/sign/upload', methods=['POST'])
@requires_auth
def upload(current_user=None):
    pubkey = request.files['file']
    username = request.form['username']
    try:
        req = post(APP.config['CASSH_URL'] + '/client' +
            auth_url(current_user['name'], password=current_user['password'], \
                prefix='?username=%s' % username), data=pubkey, verify=False)
    except ConnectionError:
        return Response('Connection error : %s' % APP.config['CASSH_URL'])
    if 'Error' in req.text:
        return Response(req.text)

    with open(path.join(APP.config['UPLOAD_FOLDER'], current_user['name']), 'w') as f:
        f.write(req.text)

    return send_from_directory(APP.config['UPLOAD_FOLDER'], current_user['name'], \
        attachment_filename='id_rsa-cert.pub', as_attachment=True)

# Route that will process the file upload
@APP.route('/add/send', methods=['POST'])
@requires_auth
def send(current_user=None):
    pubkey = request.files['file']
    username = request.form['username']
    try:
        req = put(APP.config['CASSH_URL'] + '/client' +
            auth_url(current_user['name'], password=current_user['password'], \
                prefix='?username=%s' % username), data=pubkey, verify=False)
    except ConnectionError:
        return Response('Connection error : %s' % APP.config['CASSH_URL'])
    if 'Error' in req.text:
        return Response(req.text)
    return redirect('/status')

@APP.errorhandler(404)
def page_not_found(_):
    """ Display error page """
    return render_template('404.html'), 404

if __name__ == '__main__':
    CONTEXT = SSLContext(PROTOCOL_TLSv1_2)
    CONTEXT.load_cert_chain(APP.config['SSL_PUB_KEY'], APP.config['SSL_PRIV_KEY'])
    PORT = int(getenv('PORT', 443))
    APP.run(debug=True, host='0.0.0.0', port=PORT, ssl_context=CONTEXT)
