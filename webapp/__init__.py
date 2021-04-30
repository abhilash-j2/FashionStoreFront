import os
from flask import Flask, render_template, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from jproperties import Properties

from flask_cors import CORS, cross_origin
from flask_cachecontrol import FlaskCacheControl

with open('DB_credentials.prop','rb') as f:
    p = Properties()
    p.load(f,"utf-8")

username = p.get("DB_username").data
password = p.get("DB_password").data
aws_endpoint = p.get("Aws_endpoint").data
port = p.get("Port").data
db_name = p.get("DB_name").data
secret_key = p.get("Secret_key").data

#print(secret_key)
#print(f'{username}+{password}+{aws_endpoint}+{port}+{db_name}+{secret_key}')


app = Flask(__name__)

# DB configuration
app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql+psycopg2://{username}:{password}@{aws_endpoint}:{port}/{db_name}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {"pool_pre_ping":True,"pool_recycle":1800}
app.config['SECRET_KEY'] = secret_key 
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# Login manager
login_manager = LoginManager(app)
login_manager.login_view = "login_page"
login_manager.login_message_category = 'error'

# Cache control
flask_cache_control = FlaskCacheControl()
flask_cache_control.init_app(app)

cors = CORS(app, allow_headers='Content-Type', CORS_SEND_WILDCARD=True)

from webapp import routes


#with open('DB_credentials.prop','wb') as f:
#    p.store(f,encoding='utf-8')

# @app.route('/about/<username>')
# def about_page(username):
#     return f'<h2>This is the about page of {username}</h2>'

# if __name__ == "__main__":
#     app.run(debug=True)