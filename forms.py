from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, FloatField, SelectField, DateField
from wtforms.validators import DataRequired, Email, EqualTo, Length


class RegistrationForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[
        DataRequired(message='Введите имя пользователя'),
        Length(min=3, max=64, message='От 3 до 64 символов')
    ])
    email = StringField('Email', validators=[
        DataRequired(message='Введите ваш email'),
        Email(message='Некорректный email')
    ])
    password = PasswordField('Пароль', validators=[
        DataRequired(message='Введите пароль'),
        Length(min=6, message='Пароль должен содержать минимум 6 символов')
    ])
    confirm_password = PasswordField('Подтвердите пароль', validators=[
        DataRequired(message='Подтвердите пароль'),
        EqualTo('password', message='Пароли не совпадают')
    ])
    submit = SubmitField('Зарегистрироваться')


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[
        DataRequired(message='Введите email'),
        Email(message='Некорректный email')
    ])
    password = PasswordField('Пароль', validators=[DataRequired(message='Введите пароль')])
    remember = BooleanField('Запомнить меня')
    submit = SubmitField('Войти')


class SubscriptionForm(FlaskForm):
    name = StringField('Название', validators=[DataRequired(message='Введите название')])
    price = FloatField('Стоимость', validators=[DataRequired(message='Введите стоимость')])
    next_payment = DateField('Дата следующего платежа', validators=[DataRequired(message='Выберите дату')], format='%Y-%m-%d')
    category = SelectField('Категория', coerce=int, validators=[DataRequired(message='Выберите категорию')])
    submit = SubmitField('Добавить')


class EditSubscriptionForm(FlaskForm):
    name = StringField('Название', validators=[DataRequired(message='Введите название')])
    price = FloatField('Стоимость', validators=[DataRequired(message='Введите стоимость')])
    next_payment = DateField('Дата следующего платежа', validators=[DataRequired(message='Выберите дату')], format='%Y-%m-%d')
    category = SelectField('Категория', coerce=int, validators=[DataRequired(message='Выберите категорию')])
    submit = SubmitField('Сохранить изменения')