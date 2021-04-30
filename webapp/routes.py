from webapp import app
from flask import render_template, redirect, url_for, flash, get_flashed_messages, send_file, make_response, request
import requests
#from webapp.module import Item
from webapp.forms import RegisterForm, LoginForm
from webapp.module import User, Products, Images, Interactions
from webapp import db, login_manager, cross_origin
from flask_login import login_user, logout_user, login_required, current_user

import io
from skimage.io import imread
import pytz
from datetime import datetime
import json


@app.route('/home')
def home_page():
    return render_template('home.html')

# @app.route('/market')
# @login_required
# def market_page():
#     items = Item.query.all()
#     return render_template('market.html',items=items)

@app.route('/register', methods=['GET','POST'])
def register_page():
    form = RegisterForm()
    if form.validate_on_submit():
        user_to_create = User(username=form.username.data,
                                email_address=form.email_address.data,
                                password=form.password1.data)
        db.session.add(user_to_create)
        db.session.commit()

        login_user(user_to_create)
        flash(f'Account created successfully! You are now logged in as  {user_to_create.username}', category='success')
        return redirect(url_for('home_page'))
    if form.errors != {}: # if there are no errors from the validations
        for err_msg in form.errors.values():
            flash(f'There was an error with creating a user: {err_msg}', category='danger')

    return render_template('register.html',form = form)

@app.route('/login',methods=['GET','POST'])
def login_page():
    form = LoginForm()
    if form.validate_on_submit():
        attempted_user = User.query.filter_by(username=form.username.data).first()
        if attempted_user and attempted_user.check_password_correction(attempted_password=form.password1.data):
            login_user(attempted_user)
            flash(f'Success! you are logged in as: {attempted_user.username}', category='success')
            return redirect(url_for('homepage'))

        else:
            flash('Username and Password are not a match! Please try again', category='danger')
    return render_template('login.html',form=form)

@app.route('/logout')
def logout_page():
    logout_user()
    flash('You have been logged out!', category='info')
    return redirect(url_for('homepage'))

@app.route('/')
@app.route("/homepage")
def homepage():
    return render_template("homepage.html")

@app.route("/product/<int:product_id>")
def product_page(product_id):
    # Pass product id on click of product image
    # Make db call to get product image paths
    # pass to template
    print(product_id)
    product = Products.query.filter_by(product_id=product_id).first()
    images = Images.query.filter_by(product_id = product_id, is_main_image=True).all()
    interaction = db.session.query(Interactions).filter_by(user_id=current_user.id, product_id=product.product_id).all()
    print(product)
    print(product.images)
    print(product.interactions)
    print(images)

    # img_path_array = [
    # "women/dresses/casual_and_day_dresses/54686996/54686996_0.jpeg",
    # "women/dresses/casual_and_day_dresses/54686996/54686996_1.jpeg",
    # "women/dresses/casual_and_day_dresses/54686996/54686996_3.jpeg"]
    
    has_user_rated = True if len(interaction) > 0 else False
    user_rating = interaction[0].rating if len(interaction) > 0 else 0
    product_info = {
        'img_path_array' : [image.image_path for image in product.images],
        'avg_rating' : calc_avg_rating(product),
        'user_rating' : user_rating,
        'has_user_rated': has_user_rated,
        'product_name' : product.product_name,
        'product_id' : product.product_id
    }
 
    return render_template("productPage.html", product_info=product_info)

def calc_avg_rating(product):
    avg_rating = 0 if len(product.interactions) == 0 else (sum([interaction.rating for interaction in product.interactions])/len(product.interactions))
    return avg_rating

@app.route('/imageSearch')
@login_required
def imageSearch():
    return render_template("image_search.html")

@app.route('/preferenceLearner')
@login_required
def preferenceLearner():
    return render_template("preference_learner.html")

@app.route('/rate',methods=['POST'])
def rate_product():
    request_data = json.loads(request.data)
    print(request.get_json())
    print("=========")
    print(request_data)
    rating = request_data['rating']
    product_id = request_data['product_id']
    user_id = current_user.id
    time_stamp = datetime.now(pytz.timezone('US/Eastern'))
    interaction = db.session.query(Interactions).filter_by(user_id=user_id, product_id=product_id)
    print(f"len : {len(interaction.all())}")
    if len(interaction.all()) == 0:
        interaction = Interactions(user_id =user_id, product_id=product_id, rating=rating, time_stamp= time_stamp)
        db.session.add(interaction)
    else:
        interaction.update({"rating":rating, "time_stamp":time_stamp})
    db.session.commit()
    print((current_user.username,current_user.id))
    product = Products.query.filter_by(product_id=product_id).first()
    return {"avg_rating": calc_avg_rating(product)}

@app.route('/uploader')
def uploader():
    # return "Homepageview"
    return render_template('uploader.html')


ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', "jfif","tiff"])

def allowed_file(filename):
    """
    :param filename: 
    :return: 
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


def query_es(user_query):
    script_query = {
        "script_score": {
            "query": {"match_all": {}},
            "script": {
                "source": "cosineSimilarity(params.query_vector, doc['image_vector'])",
                "params": {"query_vector": user_query}
                        }
                    }
                }
    
    cards = []
    try:    
        with Elasticsearch([{"host": host, "port":"9200"}]) as es: 
            res = es.search(index='similarity-search',body={"from":0,"size": 5,"query": script_query,"_source":["picture_id","product_id"]})
            for dic in res['hits']['hits']:
                prod_id = dic['_source']['product_id']
                pic_id = dic['_source']['picture_id']
                score = dic['_score']
                picture = url_process_imgdict(df[df["picture_id"]==pic_id].to_dict("records")[0]["picture"])
                cards.append({"prod_id" : prod_id, "pic_id" : pic_id, "score":score, "img" : picture})

    except Exception as e:
        print(e)   

    return cards
MODEL_URL = "http://ec2-18-217-197-173.us-east-2.compute.amazonaws.com:8000/get-features"
def get_image_vector(image):
    dictToSend = {"image":image.tolist()}
    res = requests.post(MODEL_URL, json=dictToSend)
    # print (('response from server:',res.text))
    dictFromServer = res.json()
    return dictFromServer["features"]


@app.route('/upload', methods=['GET','POST'])
@cross_origin(origins='*', send_wildcard=True)
def upload_file():
    if request.method == 'POST':
        file = request.files['file']
        if file and allowed_file(file.filename):
            # filename = secure_filename(file.filename)
            with io.BytesIO() as byte_io:
                byte_io.write(file.read())
                byte_io.seek(0)
                img_arr = imread(byte_io)

            img_arr = img_arr[:,:,:3]
            features = get_image_vector(img_arr)
            # card_data = query_es(features)
            print(features)
            #return render_template('upload_result.html', mainimg = get_base64_from_img(img_arr), card_data = card_data )

