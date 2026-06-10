from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), nullable=False, unique=True)
    email = db.Column(db.String(120), nullable=False, unique=True)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    subscriptions = db.relationship('Subscription', backref='owner', lazy='dynamic', cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'


class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)

    subscriptions = db.relationship('Subscription', backref='category_ref', lazy='dynamic')

    def __repr__(self):
        return f'<Category {self.name}>'


class Subscription(db.Model):
    __tablename__ = 'subscriptions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    next_payment = db.Column(db.Date, nullable=False)
    category = db.Column(db.String(50))
    color = db.Column(db.String(50), default='bg-gray-100 text-gray-600')
    icon_name = db.Column(db.String(50), default='fa-credit-card')
    currency = db.Column(db.String(10), default='₽')
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def update_next_payment(self):
        from datetime import datetime
        today = datetime.now().date()
        while self.next_payment < today:
            if self.next_payment.month == 12:
                self.next_payment = self.next_payment.replace(year=self.next_payment.year + 1, month=1)
            else:
                self.next_payment = self.next_payment.replace(month=self.next_payment.month + 1)

    def __repr__(self):
        return f'<Subscription {self.name}>'


class PaymentLog(db.Model):
    __tablename__ = 'payment_logs'
    id = db.Column(db.Integer, primary_key=True)
    subscription_id = db.Column(db.Integer, db.ForeignKey('subscriptions.id'), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='success')

    def __repr__(self):
        return f'<PaymentLog {self.amount}>'