from flask import Flask, render_template, url_for,send_file, make_response, request
from flask_cors import CORS, cross_origin

app = Flask(__name__)
cors = CORS(app, allow_headers='Content-Type', CORS_SEND_WILDCARD=True)


@app.route("/")
def homepage():
    return render_template("homepage.html")







if __name__ == '__main__':
   app.run(debug = True)