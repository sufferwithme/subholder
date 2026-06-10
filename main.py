from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_login import LoginManager, login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from calendar import monthrange
from models import db, User, Subscription, Category, PaymentLog
from forms import RegistrationForm, LoginForm, SubscriptionForm, EditSubscriptionForm


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'dev-secret-key-change-in-production'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///subscriptions.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    login_manager.login_message = 'Пожалуйста, войдите для доступа к этой странице.'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    with app.app_context():
        db.create_all()
        default_categories = ['Развлечения', 'Музыка', 'Сервисы', 'Здоровье', 'Интернет', 'Связь', 'Облако', 'Другое']
        for cat_name in default_categories:
            if not Category.query.filter_by(name=cat_name).first():
                db.session.add(Category(name=cat_name))
        db.session.commit()

    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        return render_template('index.html')

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        form = RegistrationForm()
        if form.validate_on_submit():
            user = User.query.filter_by(email=form.email.data).first()
            if user:
                flash('Пользователь с таким email уже зарегистрирован', 'danger')
                return render_template('register.html', form=form)
            new_user = User(username=form.username.data, email=form.email.data)
            new_user.set_password(form.password.data)
            db.session.add(new_user)
            db.session.commit()
            flash('Вы зарегистрировались. Теперь вы можете авторизоваться', 'success')
            return redirect(url_for('login'))
        return render_template('register.html', form=form)

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        form = LoginForm()
        if form.validate_on_submit():
            user = User.query.filter_by(email=form.email.data).first()
            if user and user.check_password(form.password.data):
                login_user(user, remember=form.remember.data)
                flash('Вы успешно вошли!', 'success')
                return redirect(url_for('dashboard'))
            flash('Неверный email или пароль', 'danger')
        return render_template('login.html', form=form)

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        flash('Вы вышли из системы', 'info')
        return redirect(url_for('index'))

    @app.route('/dashboard')
    @login_required
    def dashboard():
        subscriptions = current_user.subscriptions.all()
        for sub in subscriptions:
            sub.update_next_payment()
        db.session.commit()

        total_monthly = sum(s.price for s in subscriptions) if subscriptions else 0
        total_yearly = total_monthly * 12

        spend_data = []
        today = datetime.now().date()
        for i in range(5, -1, -1):
            month_date = today.replace(day=1) - timedelta(days=i * 30)
            month_name = month_date.strftime('%b')
            monthly_sum = 0
            for sub in subscriptions:
                if sub.next_payment.year == month_date.year and sub.next_payment.month == month_date.month:
                    monthly_sum += sub.price
            spend_data.append({'name': month_name, 'amount': monthly_sum})

        upcoming = sorted(subscriptions, key=lambda x: x.next_payment)[:3]

        return render_template('dashboard.html',
                               subscriptions=subscriptions,
                               total_monthly=total_monthly,
                               total_yearly=total_yearly,
                               spend_data=spend_data,
                               upcoming=upcoming)

    @app.route('/subscriptions')
    @login_required
    def subscriptions():
        subs = current_user.subscriptions.all()
        for sub in subs:
            sub.update_next_payment()
        db.session.commit()
        categories = Category.query.all()
        return render_template('subscriptions.html', subscriptions=subs, categories=categories)

    @app.route('/subscriptions/add', methods=['GET', 'POST'])
    @login_required
    def add_subscription():
        form = SubscriptionForm()
        form.category.choices = [(c.id, c.name) for c in Category.query.all()]
        if form.validate_on_submit():
            category_colors = {
                'Развлечения': ('bg-red-100 text-red-600', 'fa-film'),
                'Музыка': ('bg-green-100 text-green-600', 'fa-music'),
                'Сервисы': ('bg-yellow-100 text-yellow-600', 'fa-cloud'),
                'Здоровье': ('bg-blue-100 text-blue-600', 'fa-heartbeat'),
                'Интернет': ('bg-purple-100 text-purple-600', 'fa-wifi'),
                'Связь': ('bg-rose-100 text-rose-600', 'fa-phone'),
                'Облако': ('bg-sky-100 text-sky-600', 'fa-database'),
                'Другое': ('bg-gray-100 text-gray-600', 'fa-credit-card')
            }
            category = Category.query.get(form.category.data)
            color, icon = category_colors.get(category.name, ('bg-gray-100 text-gray-600', 'fa-credit-card'))
            sub = Subscription(
                user_id=current_user.id,
                category_id=form.category.data,
                name=form.name.data,
                price=form.price.data,
                next_payment=form.next_payment.data,
                category=category.name,
                color=color,
                icon_name=icon
            )
            db.session.add(sub)
            db.session.commit()
            sub.update_next_payment()
            db.session.commit()
            flash('Подписка добавлена!', 'success')
            return redirect(url_for('subscriptions'))
        return render_template('add_subscription.html', form=form)

    @app.route('/subscriptions/edit/<int:id>', methods=['GET', 'POST'])
    @login_required
    def edit_subscription(id):
        sub = Subscription.query.get_or_404(id)
        if sub.user_id != current_user.id:
            flash('Нет прав для редактирования этой подписки.', 'danger')
            return redirect(url_for('subscriptions'))

        form = EditSubscriptionForm()
        form.category.choices = [(c.id, c.name) for c in Category.query.all()]

        if form.validate_on_submit():
            category_colors = {
                'Развлечения': ('bg-red-100 text-red-600', 'fa-film'),
                'Музыка': ('bg-green-100 text-green-600', 'fa-music'),
                'Сервисы': ('bg-yellow-100 text-yellow-600', 'fa-cloud'),
                'Здоровье': ('bg-blue-100 text-blue-600', 'fa-heartbeat'),
                'Интернет': ('bg-purple-100 text-purple-600', 'fa-wifi'),
                'Связь': ('bg-rose-100 text-rose-600', 'fa-phone'),
                'Облако': ('bg-sky-100 text-sky-600', 'fa-database'),
                'Другое': ('bg-gray-100 text-gray-600', 'fa-credit-card')
            }
            category = Category.query.get(form.category.data)
            color, icon = category_colors.get(category.name, ('bg-gray-100 text-gray-600', 'fa-credit-card'))

            sub.name = form.name.data
            sub.price = form.price.data
            sub.next_payment = form.next_payment.data
            sub.category_id = form.category.data
            sub.category = category.name
            sub.color = color
            sub.icon_name = icon

            db.session.commit()
            flash('Подписка обновлена!', 'success')
            return redirect(url_for('subscriptions'))

        elif request.method == 'GET':
            form.name.data = sub.name
            form.price.data = sub.price
            form.next_payment.data = sub.next_payment
            form.category.data = sub.category_id

        return render_template('edit_subscription.html', form=form, subscription=sub)

    @app.route('/subscriptions/delete/<int:id>', methods=['POST'])
    @login_required
    def delete_subscription(id):
        sub = Subscription.query.get_or_404(id)
        if sub.user_id != current_user.id:
            flash('Нет прав для удаления этой подписки.', 'danger')
            return redirect(url_for('subscriptions'))
        db.session.delete(sub)
        db.session.commit()
        flash('Подписка удалена.', 'success')
        return redirect(url_for('subscriptions'))

    @app.route('/calendar')
    @login_required
    def calendar():
        year = request.args.get('year', type=int)
        month = request.args.get('month', type=int)
        now = datetime.now()
        if not year or not month:
            year = now.year
            month = now.month

        subs = current_user.subscriptions.all()
        for sub in subs:
            sub.update_next_payment()
        db.session.commit()

        def add_month(d):
            if d.month == 12:
                next_month = d.replace(year=d.year + 1, month=1, day=1)
            else:
                next_month = d.replace(month=d.month + 1, day=1)
            try:
                return next_month.replace(day=d.day)
            except ValueError:
                if next_month.month == 12:
                    return next_month.replace(year=next_month.year + 1, month=1, day=1) - timedelta(days=1)
                else:
                    return next_month.replace(month=next_month.month + 1, day=1) - timedelta(days=1)

        subs_by_date = {}
        today = now.date()
        for sub in subs:
            payment_date = sub.next_payment
            for _ in range(12):
                key = payment_date.strftime('%Y-%m-%d')
                if key not in subs_by_date:
                    subs_by_date[key] = []
                subs_by_date[key].append(sub)
                payment_date = add_month(payment_date)

        first_day = datetime(year, month, 1)
        start_weekday = first_day.weekday()
        start_offset = start_weekday
        _, days_in_month = monthrange(year, month)

        calendar_rows = []
        week = []
        prev_month_date = first_day - timedelta(days=start_offset)
        for d in range(42):
            current_date = prev_month_date + timedelta(days=d)
            date_key = current_date.strftime('%Y-%m-%d')
            is_current_month = (current_date.month == month and current_date.year == year)
            is_today = (current_date.date() == today)
            week.append({
                'day': current_date.day,
                'is_current_month': is_current_month,
                'is_today': is_today,
                'subscriptions': subs_by_date.get(date_key, [])
            })
            if len(week) == 7:
                calendar_rows.append(week)
                week = []

        months_ru = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь', 'Октябрь',
                     'Ноябрь', 'Декабрь']
        month_name = f"{months_ru[month - 1]} {year}"
        prev_month_date = first_day - timedelta(days=1)
        next_month_date = first_day + timedelta(days=days_in_month)

        return render_template('calendar.html',
                               calendar_rows=calendar_rows,
                               month_name=month_name,
                               prev_year=prev_month_date.year,
                               prev_month=prev_month_date.month,
                               next_year=next_month_date.year,
                               next_month=next_month_date.month)

    @app.route('/settings', methods=['GET', 'POST'])
    @login_required
    def settings():
        if request.method == 'POST':
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')

            if username:
                current_user.username = username
            if email:
                current_user.email = email
            if password:
                if len(password) < 6:
                    flash('Пароль должен содержать минимум 6 символов', 'danger')
                    return redirect(url_for('settings'))
                if password != confirm_password:
                    flash('Пароли не совпадают', 'danger')
                    return redirect(url_for('settings'))
                current_user.set_password(password)

            db.session.commit()
            flash('Настройки успешно сохранены!', 'success')
            return redirect(url_for('settings'))
        return render_template('settings.html')

    @app.route('/api/subscriptions', methods=['GET'])
    @login_required
    def api_get_subscriptions():
        subs = current_user.subscriptions.all()
        return jsonify([{
            'id': s.id,
            'name': s.name,
            'price': s.price,
            'currency': s.currency,
            'next_payment': s.next_payment.strftime('%Y-%m-%d'),
            'category': s.category,
            'color': s.color,
            'iconName': s.icon_name
        } for s in subs])

    @app.route('/api/subscriptions/<int:id>', methods=['DELETE'])
    @login_required
    def api_delete_subscription(id):
        sub = Subscription.query.get_or_404(id)
        if sub.user_id != current_user.id:
            return jsonify({'error': 'Нет прав'}), 403
        db.session.delete(sub)
        db.session.commit()
        return jsonify({'message': 'Подписка удалена'}), 200

    @app.errorhandler(404)
    def not_found(error):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('500.html'), 500

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)