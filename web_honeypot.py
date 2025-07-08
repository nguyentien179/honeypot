from flask import Flask, render_template, request, redirect, make_response
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
import os


###logging format
logging_format = logging.Formatter('%(asctime)s %(messages)s')

###http logger

###logger
funnel_logger = logging.getLogger('HttpLogger')
funnel_logger.setLevel(logging.INFO)
funnel_handler = RotatingFileHandler('http_audits.log', maxBytes=2000, backupCount=5)
funnel_handler.setFormatter(logging_format)
funnel_logger.addHandler(funnel_handler)

###baseline honeybot

def web_honeypot(input_username = "admin", input_password = "admin"):
    app = Flask(__name__)

    @app.route('/')

    def index():
        return render_template('wp-admin.html')
    
    @app.route("/wp-admin-login", methods=['POST'])
    
    def login():
        username = request.form['username']
        password = request.form['password']

        ip_addr = request.remote_addr
        funnel_logger.info(f'Client with ip {ip_addr} enter username: {username} and password: {password}')

        if username == input_username and password == input_password:
            funnel_logger.info(f'Client with ip {ip_addr} logined')
            return 'DEEBOODAH'
        else:
            funnel_logger.info(f'Client with ip {ip_addr} login failed')
            return "invalid username and password"
            
        
    return app

def run_web_honeypot(port=5000,input_username = "admin", input_password = "admin"):
    run_web_honeypot_app = web_honeypot(input_username= input_username, input_password=input_password)
    run_web_honeypot_app.run(debug=True, port = port, host="0.0.0.0")

    return run_web_honeypot_app