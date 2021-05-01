from webapp import app
from flask import render_template, redirect, url_for, flash, get_flashed_messages, send_file, make_response, request, safe_join
import requests
#from webapp.module import Item
from webapp.forms import RegisterForm, LoginForm
from webapp.module import User, Products, Images, Interactions
from webapp import db, login_manager, cross_origin
from flask_login import login_user, logout_user, login_required, current_user

from webapp.elasticModules import recommendations_for_textsearch_query, get_visual_similarity

import io
from skimage.io import imread
import pytz
from datetime import datetime
import json
import random
import pandas as pd
import matplotlib.pyplot as plt
import base64

plt.switch_backend('agg')

from sqlalchemy import select, func

from flask_cachecontrol import dont_cache

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

def get_product_info_by_number(product_number):
    product = Products.query.filter_by(product_number=product_number).first()
    product_id = product.product_id
    images = Images.query.filter_by(product_id = product_id, is_main_image=True).all()
    interaction = db.session.query(Interactions).filter_by(user_id=current_user.id, product_id=product.product_id).all()
    print(product)
    print(product.images)
    print(product.interactions)
    print(images)
    
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
    return product_info

def get_product_info(product_id):
    product = Products.query.filter_by(product_id=product_id).first()
    images = Images.query.filter_by(product_id = product_id, is_main_image=True).all()
    interaction = db.session.query(Interactions).filter_by(user_id=current_user.id, product_id=product.product_id).all()
    print(product)
    print(product.images)
    print(product.interactions)
    print(images)
    
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
    return product_info

@app.route("/product/<int:product_id>")
@dont_cache()
def product_page(product_id):
    # Pass product id on click of product image
    # Make db call to get product image paths
    # pass to template
    print(product_id)
    product_info = get_product_info(product_id)
 
    return render_template("productPage.html", product_info=product_info)

def calc_avg_rating(product):
    avg_rating = 0 if len(product.interactions) == 0 else (sum([interaction.rating for interaction in product.interactions])/len(product.interactions))
    return avg_rating

@app.route('/imageSearch')
@dont_cache()
@login_required
def imageSearch():
    return render_template("image_search.html")


def get_unrated_product_ids(user_id):
    # Get rated products for user
    interactions = db.session.query(Interactions).filter_by(user_id=user_id).all()
    rated_products = [interaction.product_id for interaction in interactions]
    # Get all the products
    # products = db.session.query(Products).all()
    # products = [product.product_id for product in products]

    total_rated = len(rated_products)
    
    with open("webapp/static/product_ids.json", "r") as f:
        products = json.load(f)
    total_products = len(products)
    # Get unrated 
    products = list(set(products) - set(rated_products))
    return {
        "unrated_product_ids" : products,
        "total_rated" : total_rated,
        "total_products" : total_products
    }

@app.route('/preferenceLearner')
@dont_cache()
@login_required
def preferenceLearner():
    product_info = None

    user_id = current_user.id
    products_dict = get_unrated_product_ids(user_id)

    no_more_products = (products_dict["total_rated"] == products_dict["total_products"] )
    unrated_products = products_dict["unrated_product_ids"]

    if not no_more_products:
        random.shuffle(unrated_products)
        product_id = unrated_products[0]
        product_info = get_product_info(product_id)


    return render_template("preference_learner.html", product_info=product_info, 
                        no_more_products= no_more_products,
                        no_rated = str(products_dict["total_rated"]) ,
                        total_products = str(products_dict["total_products"] ))

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



MODEL_URL = "http://ec2-18-217-197-173.us-east-2.compute.amazonaws.com:8000/get-features"
def get_image_vector(image):
    dictToSend = {"image":image.tolist()}
    res = requests.post(MODEL_URL, json=dictToSend)
    # print (('response from server:',res.text))
    dictFromServer = res.json()
    return dictFromServer["features"]


@app.route('/upload', methods=['GET','POST'])
@login_required
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
            print(".. Querying tensorflow ...")
            features = get_image_vector(img_arr)
            print(".. Obtained tensorflow vector ...")
            card_data = get_visual_similarity(features)
            print(card_data)
            query = db.session.query(Products).filter(Products.product_number.in_(card_data["product_number"].tolist()))
            prods = query.all()
            prod_df  = pd.DataFrame([prod.to_dict() for prod in prods])
            print("-----")
            prod_ids = prod_df["product_id"].tolist()
            print(prod_ids)
            print(type(prod_ids))
            images = db.session.query(Images).filter(Images.product_id.in_(prod_ids)).filter(Images.is_main_image == True).all()
            images = pd.DataFrame([img.to_dict() for img in images])
    
            prod_df = prod_df.merge(images, on="product_id")
            prod_df = prod_df.merge(card_data, on="product_number")
            prod_df = prod_df.to_dict("records")
            return render_template('upload_results.html', mainimg = get_base64_from_img(img_arr), card_data = prod_df )
    return "done upload"


def get_base64_from_img(img_arr):
    plt.imshow(img_arr)
    plt.axis("off")
    with io.BytesIO() as figfile:
        plt.savefig(figfile, format='png')
        figfile.seek(0)
        figdata_png = base64.b64encode(figfile.getvalue()).decode("utf-8")
    return figdata_png


@app.route('/browse')
@login_required
def browsePage():
    
    return render_template("imageCards.html",products=[], previous_query=None)
    return render_template("browsePage.html")


@app.route('/searchText', methods=["POST"])
def search_text():
    request_data = request.form["query"]
    print(request.form)
    #request_data = json.loads(request.data)
    print(request_data)
    result_df = recommendations_for_textsearch_query(request_data)
    print(result_df)
    print(result_df.info())
    #prod_number = result_df["product-number"]
    # result_df["product-number"] = result_df["product-number"].values.astype(int)
    #print(prod_number)
    query = db.session.query(Products).filter(Products.product_number.in_(result_df["product-number"].tolist()))
    prods = query.all()
    prod_df  = pd.DataFrame([prod.to_dict() for prod in prods])
    print("-----")
    prod_number = prod_df["product_id"].tolist()
    print(prod_number)
    print(type(prod_number))
    images = db.session.query(Images).filter(Images.product_id.in_(prod_number)).filter(Images.is_main_image == True).all()
    images = pd.DataFrame([img.to_dict() for img in images])
    print(result_df)
    print(prod_df)
    result_df["product-number"] = pd.to_numeric(result_df["product-number"])
    prod_df = prod_df.merge(images, on = "product_id")
    prod_df = prod_df.merge(result_df[["product-number","score_final"]], left_on="product_number", right_on="product-number")
    prod_df = prod_df.sort_values("score_final", ascending=False)
    print(prod_df)
    print(prod_df.info())
    print("-Im----")
    prod_df = prod_df.to_dict("records")


    return render_template("imageCards.html",products=prod_df, previous_query=request_data)



@app.route('/product_names')
def product_names():
    safe_path = safe_join('static', "product_names.json")
    print(safe_path)
    return send_file(safe_path, as_attachment=False)