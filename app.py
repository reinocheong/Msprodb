import os
from flask import Flask, render_template, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.middleware.proxy_fix import ProxyFix
from models import db, User
from forms import LoginForm, RegisterForm

login_manager = LoginManager()
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

def create_app():
    app = Flask(__name__)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')

    database_url = os.environ.get('DATABASE_URL', 'sqlite:///local_dev.db')
    if database_url and database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    login_manager.init_app(app)

    @app.route('/')
    @app.route('/index')
    @login_required
    def index():
        # Dummy data for the new template
        dummy_summary = {
            'total_booking_revenue': 12345.67,
            'total_monthly_expenses': 3456.78,
            'gross_profit': 8888.89,
            'management_fee': 2666.67,
            'monthly_income': 6222.22,
            'total_occupancy_rate': 75.5
        }
        dummy_analysis = {
            'total_bookings_count': 150,
            'average_duration': 2.5,
            'average_daily_rate': 450.75,
            'revpar': 340.50,
            'average_monthly_revenue': 15000.00,
            'average_monthly_expenses': 4000.00
        }
        return render_template('index.html', 
                               username=current_user.username,
                               summary=dummy_summary,
                               analysis=dummy_analysis,
                               years_options=[2024, 2023],
                               default_year='2024',
                               months_options=[{'value': i, 'text': f'{i}月'} for i in range(1, 13)],
                               room_types=['所有房型', '大床房', '双床房'],
                               current_user_role=current_user.role,
                               edit_booking_url_pattern='/edit_booking/{}')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('index'))

        form = LoginForm()
        if form.validate_on_submit():
            user = User.query.filter_by(email=form.email.data).first()
            if user and user.check_password(form.password.data):
                login_user(user)
                return redirect(url_for('index'))
            else:
                flash('Invalid email or password.', 'danger')
        return render_template('login.html', form=form)

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for('index'))

        form = RegisterForm()
        if form.validate_on_submit():
            existing_user = User.query.filter_by(email=form.email.data).first()
            if existing_user is None:
                new_user = User(username=form.username.data, email=form.email.data)
                new_user.set_password(form.password.data)
                db.session.add(new_user)
                db.session.commit()
                flash('Registration successful! Please log in.', 'success')
                return redirect(url_for('login'))
            flash('A user with that email address already exists.', 'danger')
        return render_template('register.html', form=form)

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        return redirect(url_for('login'))

    # Placeholder routes for the new template
    @app.route('/reports')
    @login_required
    def reports():
        flash('报表中心功能正在开发中。', 'info')
        return redirect(url_for('index'))

    @app.route('/calendar_view')
    @login_required
    def calendar_view():
        flash('预订日历功能正在开发中。', 'info')
        return redirect(url_for('index'))

    @app.route('/admin_panel')
    @login_required
    def admin_panel():
        flash('后台管理功能正在开发中。', 'info')
        return redirect(url_for('index'))

    @app.route('/add_booking')
    @login_required
    def add_booking():
        flash('新增预订功能正在开发中。', 'info')
        return redirect(url_for('index'))

    @app.route('/api/filter_data')
    @login_required
    def filter_data():
        return {} # Return empty JSON

    @app.route('/api/chart_data')
    @login_required
    def chart_data():
        return {} # Return empty JSON
        
    @app.route('/api/detailed_data')
    @login_required
    def detailed_data():
        return {} # Return empty JSON

    @app.route('/download_monthly_statement')
    @login_required
    def download_monthly_statement():
        flash('下载月结单功能正在开发中。', 'info')
        return redirect(url_for('index'))

    return app
