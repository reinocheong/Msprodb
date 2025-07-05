import os
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from sqlalchemy import extract
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_migrate import Migrate
from dotenv import load_dotenv

from .models import db, User, Booking, Expense
from .forms import LoginForm, RegisterForm

load_dotenv()

login_manager = LoginManager()
login_manager.login_view = 'login'
migrate = Migrate()


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

def create_app():
    app = Flask(__name__, static_folder='static', template_folder='templates')
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')

    database_url = os.environ.get('DATABASE_URL', 'sqlite:///local_dev.db')
    if database_url and database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    @app.route('/')
    @app.route('/index')
    @login_required
    def index():
        # Query real data from the database
        bookings = Booking.query.all()
        expenses = Expense.query.all()

        # --- Perform Calculations ---
        total_booking_revenue = sum(b.total_revenue for b in bookings if b.total_revenue)
        total_monthly_expenses = sum(e.debit for e in expenses if e.debit)
        gross_profit = total_booking_revenue - total_monthly_expenses
        management_fee = gross_profit * 0.30  # 30% management fee
        monthly_income = gross_profit - management_fee
        
        # Occupancy rate calculation needs more context (e.g., total available room-nights)
        # For now, we'll use a placeholder value.
        total_occupancy_rate = 0 
        if bookings:
            # A simple placeholder logic: (booked days / (365 * num_rooms))
            # This is not accurate and needs to be replaced with real logic.
            # Assuming 5 rooms for calculation.
            total_days_booked = sum(b.duration for b in bookings if b.duration)
            total_occupancy_rate = (total_days_booked / (365 * 5)) * 100 if total_days_booked else 0


        summary = {
            'total_booking_revenue': total_booking_revenue,
            'total_monthly_expenses': total_monthly_expenses,
            'gross_profit': gross_profit,
            'management_fee': management_fee,
            'monthly_income': monthly_income,
            'total_occupancy_rate': total_occupancy_rate
        }

        # --- Analysis data (placeholders for now, needs real logic) ---
        analysis = {
            'total_bookings_count': len(bookings),
            'average_duration': (sum(b.duration for b in bookings if b.duration) / len(bookings)) if bookings else 0,
            'average_daily_rate': (sum(b.price for b in bookings if b.price) / len(bookings)) if bookings else 0,
            'revpar': 0, # Placeholder
            'average_monthly_revenue': 0, # Placeholder
            'average_monthly_expenses': 0 # Placeholder
        }

        # --- Options for filters ---
        # Get distinct years from bookings and expenses
        booking_years = db.session.query(db.extract('year', Booking.checkin_date)).distinct().all()
        expense_years = db.session.query(db.extract('year', Expense.date)).distinct().all()
        all_years = sorted(set([y[0] for y in booking_years] + [y[0] for y in expense_years]), reverse=True)

        # Get distinct room types (unit_name)
        room_types = db.session.query(Booking.unit_name).distinct().all()
        room_types = ['所有房型'] + sorted([r[0] for r in room_types])


        return render_template('index.html', 
                               username=current_user.username,
                               summary=summary,
                               analysis=analysis,
                               years_options=all_years,
                               default_year=str(max(all_years)) if all_years else '',
                               months_options=[{'value': i, 'text': f'{i}月'} for i in range(1, 13)],
                               room_types=room_types,
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
        # Return a correctly structured but empty/zeroed response
        empty_summary = {
            'total_booking_revenue': 0, 'total_monthly_expenses': 0,
            'gross_profit': 0, 'management_fee': 0,
            'monthly_income': 0, 'total_occupancy_rate': 0
        }
        empty_analysis = {
            'total_bookings_count': 0, 'average_duration': 0,
            'average_daily_rate': 0, 'revpar': 0,
            'average_monthly_revenue': 0, 'average_monthly_expenses': 0
        }
        return {'summary': empty_summary, 'analysis': empty_analysis}

    @app.route('/api/chart_data')
    @login_required
    def chart_data():
        return {} # Return empty JSON
        
    @app.route('/api/detailed_data')
    @login_required
    def detailed_data():
        year = request.args.get('year', type=int)
        month = request.args.get('month', type=int)
        room_type = request.args.get('room_type')

        # Start with a base query
        booking_query = Booking.query
        expense_query = Expense.query

        if year:
            booking_query = booking_query.filter(extract('year', Booking.checkin_date) == year)
            expense_query = expense_query.filter(extract('year', Expense.date) == year)
        
        if month:
            booking_query = booking_query.filter(extract('month', Booking.checkin_date) == month)
            expense_query = expense_query.filter(extract('month', Expense.date) == month)

        if room_type and room_type != '所有房型':
            booking_query = booking_query.filter(Booking.unit_name == room_type)
            expense_query = expense_query.filter(Expense.unit_name == room_type)

        bookings = booking_query.all()
        expenses = expense_query.all()

        # Combine and format data
        combined_data = []
        for b in bookings:
            combined_data.append({
                'type': 'booking',
                'date': b.checkin_date.strftime('%Y-%m-%d'),
                'unit_name': b.unit_name,
                'checkin': b.checkin_date.strftime('%Y-%m-%d'),
                'checkout': b.checkout_date.strftime('%Y-%m-%d'),
                'channel': b.channel,
                'on_offline': b.on_offline,
                'booking_number': b.booking_number,
                'pax': b.pax,
                'duration': b.duration,
                'price': b.price,
                'cleaning_fee': b.cleaning_fee,
                'platform_charge': b.platform_charge,
                'total_booking_revenue': b.total_revenue,
                'additional_expense_category': None,
                'additional_expense_amount': None,
                'expense_id': None
            })
        
        for e in expenses:
            combined_data.append({
                'type': 'expense',
                'date': e.date.strftime('%Y-%m-%d'),
                'unit_name': e.unit_name,
                'checkin': None, 'checkout': None, 'channel': None, 'on_offline': None,
                'booking_number': None, 'pax': None, 'duration': None, 'price': None,
                'cleaning_fee': None, 'platform_charge': None, 'total_booking_revenue': None,
                'additional_expense_category': e.particulars,
                'additional_expense_amount': e.debit,
                'expense_id': e.id
            })
            
        # Sort by date
        combined_data.sort(key=lambda x: x['date'])

        return jsonify({'data': combined_data})

    @app.route('/download_monthly_statement')
    @login_required
    def download_monthly_statement():
        flash('下载月结单功能正在开发中。', 'info')
        return redirect(url_for('index'))

    return app
