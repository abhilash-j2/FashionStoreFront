from webapp import app
from flask import render_template, redirect, url_for, flash, get_flashed_messages
#from webapp.module import Item
from webapp.forms import RegisterForm, LoginForm
from webapp.module import User #,Item
from webapp import db, login_manager
from flask_login import login_user, logout_user, login_required, current_user

@app.route('/')
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
    return redirect(url_for('home_page'))


@app.route("/homepage")
@login_required
def homepage():
    return render_template("homepage.html")

@app.route("/product/<int:product_id>")
def product_page(product_id):
    # Pass product id on click of product image
    # Make db call to get product image paths
    # pass to template
    print(product_id)
    img_path_array = [
    "women/dresses/casual_and_day_dresses/54686996/54686996_0.jpeg",
    "women/dresses/casual_and_day_dresses/54686996/54686996_1.jpeg",
    "women/dresses/casual_and_day_dresses/54686996/54686996_3.jpeg"]

    product_info = {
        'img_path_array' : img_path_array,
        'ratings' : 3,
        'has_user_rated': False
    }

    return render_template("productPage.html", product_info=product_info)

@app.route('/rate')
def rating_page():
    print((current_user.username,current_user.id))
    return "done"
