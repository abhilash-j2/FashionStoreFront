from webapp import db, login_manager
from webapp import bcrypt
from flask_login import UserMixin

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer(), primary_key=True)
    username = db.Column(db.String(length=40), nullable=False, unique=True)
    email_address =db.Column(db.String(length=50), nullable=False, unique=True)
    password_hash = db.Column(db.String(length=60), nullable=False)
    budget = db.Column(db.Integer(), nullable=True, default=1000)
    # items = db.relationship('Item',backref='owned_user', lazy=True)

    @property
    def password(self):
        return self.password
    
    @password.setter
    def password(self, plain_text_password):
        self.password_hash = bcrypt.generate_password_hash(plain_text_password).decode('utf-8')

    def check_password_correction(self,attempted_password):
        return bcrypt.check_password_hash(self.password_hash, attempted_password)

# class Item(db.Model):
#     id = db.Column(db.Integer(),primary_key=True)
#     name = db.Column(db.String(length=30), nullable=False, unique=True)
#     price = db.Column(db.Integer(), nullable=False)
#     barcode = db.Column(db.String(length=12), nullable=False, unique=True)
#     description = db.Column(db.String(length=1024), nullable=False, unique=True)
#     owner = db.Column(db.Integer(),db.ForeignKey('user.id'))
    
#     def __repr__(self):
#         return f'Item {self.name}'

class Products(db.Model):
    product_id = db.Column(db.Integer(),primary_key=True)
    category = db.Column(db.String(length=70),nullable=False)
    sub_category = db.Column(db.String(length=70),nullable=False)
    product_number = db.Column(db.Integer(),nullable=False)

class Interactions(db.Model):
    interaction_id = db.Column(db.Integer(),primary_key=True)
    user_id = db.Column(db.Integer(),nullable=False,unique=True)
    product_id = db.Column(db.Integer(),nullable=False)
    rating = db.Column(db.Float(),nullable=False)
    time_stamp = db.Column(db.DateTime,nullable=False)
    user = db.Column(db.Integer(),db.ForeignKey('user.id'))
    product = db.Column(db.Integer(),db.ForeignKey('products.product_id'))