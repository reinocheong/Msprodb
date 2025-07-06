from flask import Blueprint, render_template, request, jsonify, send_file, make_response, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from .extensions import db
from .models import User, Booking, Expense
from .forms import LoginForm, RegistrationForm
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import calendar
from sqlalchemy import extract, func, and_

main = Blueprint('main', __name__)

# --- HELPER FUNCTIONS ---

def get_filtered_data(year, month=None, room_type=None):
    # Base queries
    bookings_query = Booking.query
    expenses_query = Expense.query

    # Year filter is mandatory
    bookings_query = bookings_query.filter(extract('year', Booking.checkin) == year)
    expenses_query = expenses_query.filter(extract('year', Expense.date) == year)

    # Month filter
    if month:
        bookings_query = bookings_query.filter(extract('month', Booking.checkin) == month)
        expenses_query = expenses_query.filter(extract('month', Expense.date) == month)

    # Room type filter
    if room_type and room_type != 'All':
        bookings_query = bookings_query.filter(Booking.unit_name == room_type)
        expenses_query = expenses_query.filter(Expense.unit_name == room_type)

    return bookings_query.all(), expenses_query.all()

def calculate_dashboard_data(bookings, expenses, year, month, room_type):
    # Summary calculations
    total_booking_revenue = sum(b.total for b in bookings if b.total)
    total_monthly_expenses = sum(e.debit for e in expenses if e.debit)
    gross_profit = total_booking_revenue - total_monthly_expenses
    management_fee = gross_profit * 0.30
    monthly_income = gross_profit - management_fee

    # Occupancy Rate Calculation
    if room_type and room_type != 'All':
        room_count = 1
    else:
        room_count = db.session.query(func.count(func.distinct(Booking.unit_name))).scalar() or 1

    if month:
        days_in_month = calendar.monthrange(year, month)[1]
        total_possible_nights = room_count * days_in_month
    else: # Annual
        total_possible_nights = room_count * 365 # Simple approximation

    total_nights_booked = sum(b.duration for b in bookings if b.duration)
    total_occupancy_rate = (total_nights_booked / total_possible_nights) * 100 if total_possible_nights > 0 else 0
    
    summary = {
        'total_booking_revenue': total_booking_revenue,
        'total_monthly_expenses': total_monthly_expenses,
        'gross_profit': gross_profit,
        'management_fee': management_fee,
        'monthly_income': monthly_income,
        'total_occupancy_rate': total_occupancy_rate,
    }

    # Analysis calculations (only for annual view)
    analysis = {}
    if not month:
        all_bookings_this_year = Booking.query.filter(extract('year', Booking.checkin) == year).all()
        all_expenses_this_year = Expense.query.filter(extract('year', Expense.date) == year).all()
        
        total_annual_revenue = sum(b.total for b in all_bookings_this_year if b.total)
        total_annual_expenses = sum(e.debit for e in all_expenses_this_year if e.debit)

        analysis = {
            'total_bookings_count': len(all_bookings_this_year),
            'average_duration': np.mean([b.duration for b in all_bookings_this_year if b.duration]) if all_bookings_this_year else 0,
            'average_daily_rate': (total_annual_revenue / sum(b.duration for b in all_bookings_this_year if b.duration)) if sum(b.duration for b in all_bookings_this_year if b.duration) > 0 else 0,
            'revpar': total_annual_revenue / (room_count * 365),
            'average_monthly_revenue': total_annual_revenue / 12,
            'average_monthly_expenses': total_annual_expenses / 12,
        }

    return summary, analysis

# --- AUTHENTICATION ROUTES ---

@main.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(id=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('main.login'))
        login_user(user, remember=form.remember_me.data)
        return redirect(url_for('main.index'))
    return render_template('login.html', title='Sign In', form=form)

@main.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.login'))

@main.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(id=form.username.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('main.login'))
    return render_template('register.html', title='Register', form=form)

# --- CORE APPLICATION ROUTES ---

@main.route('/')
@login_required
def index():
    selected_year = request.args.get('year', datetime.now().year, type=int)
    selected_month = request.args.get('month', request.args.get('month'), type=int)
    selected_room_type = request.args.get('room_type', 'All')

    bookings, expenses = get_filtered_data(selected_year, selected_month, selected_room_type)
    summary, analysis = calculate_dashboard_data(bookings, expenses, selected_year, selected_month, selected_room_type)

    # Dynamic options for filters
    years_options = db.session.query(extract('year', Booking.checkin)).distinct().order_by(extract('year', Booking.checkin).desc()).all()
    years_options = [y[0] for y in years_options if y[0]]
    
    months_options = [{'value': i, 'text': calendar.month_name[i]} for i in range(1, 13)]
    
    room_types = db.session.query(Booking.unit_name).distinct().order_by(Booking.unit_name).all()
    room_types = ['All'] + [r[0] for r in room_types if r[0]]

    return render_template('index.html',
                           title='Dashboard',
                           summary=summary,
                           analysis=analysis,
                           years_options=years_options,
                           months_options=months_options,
                           room_types=room_types,
                           default_year=str(selected_year),
                           current_user_role=current_user.role,
                           edit_booking_url_pattern=url_for('main.index') # Placeholder
                           )

# --- API ROUTES FOR CHARTS AND DYNAMIC DATA ---

@main.route('/api/chart_data')
@login_required
def chart_data():
    year = request.args.get('year', datetime.now().year, type=int)
    room_type = request.args.get('room_type', 'All')
    
    monthly_revenue = []
    monthly_expenses = []
    months = [calendar.month_name[i] for i in range(1, 13)]

    for month in range(1, 13):
        bookings, expenses = get_filtered_data(year, month, room_type)
        monthly_revenue.append(sum(b.total for b in bookings if b.total))
        monthly_expenses.append(sum(e.debit for e in expenses if e.debit))

    return jsonify({
        'months': months,
        'monthly_revenue': monthly_revenue,
        'monthly_expenses': monthly_expenses
    })

@main.route('/api/detailed_data')
@login_required
def detailed_data():
    year = request.args.get('year', datetime.now().year, type=int)
    month = request.args.get('month', type=int)
    room_type = request.args.get('room_type', 'All')

    bookings, expenses = get_filtered_data(year, month, room_type)
    
    data = []
    for b in bookings:
        data.append({
            'type': 'booking', 'date': b.checkin.strftime('%Y-%m-%d'), 'unit_name': b.unit_name,
            'checkin': b.checkin.strftime('%Y-%m-%d'), 'checkout': b.checkout.strftime('%Y-%m-%d'),
            'channel': b.channel, 'on_offline': b.on_offline, 'pax': b.pax, 'duration': b.duration,
            'price': b.price, 'cleaning_fee': b.cleaning_fee, 'platform_charge': b.platform_charge,
            'total_booking_revenue': b.total, 'booking_number': b.booking_number, 'expense_id': None,
            'additional_expense_category': None, 'additional_expense_amount': None
        })
    for e in expenses:
        data.append({
            'type': 'expense', 'date': e.date.strftime('%Y-%m-%d'), 'unit_name': e.unit_name or '_GENERAL_EXPENSE_',
            'checkin': '-', 'checkout': '-', 'channel': '-', 'on_offline': '-', 'pax': '-', 'duration': '-',
            'price': 0, 'cleaning_fee': 0, 'platform_charge': 0, 'total_booking_revenue': 0,
            'booking_number': None, 'expense_id': e.id,
            'additional_expense_category': e.particulars, 'additional_expense_amount': e.debit
        })
    
    data.sort(key=lambda x: x['date'])
    return jsonify({'data': data})