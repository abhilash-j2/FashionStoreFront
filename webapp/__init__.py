import os
from flask import Flask, render_template, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///market.db'
app.config['SECRET_KEY'] = 'f7c35f1e4e44ddedde3125e5'
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = "login_page"
login_manager.login_message_category = 'info'

from webapp import routes


# @app.route('/about/<username>')
# def about_page(username):
#     return f'<h2>This is the about page of {username}</h2>'

# if __name__ == "__main__":
#     app.run(debug=True)