from flask import Blueprint, render_template, request, jsonify, make_response, redirect, url_for, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from .extensions import db
from .models import User, Booking, Expense
from .forms import LoginForm, RegistrationForm, BookingForm, ExpenseForm
import pandas as pd
import numpy as np
from datetime import datetime
import calendar
from sqlalchemy import extract, func, or_
import math
import pdfkit
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

main = Blueprint('main', __name__)

# --- HELPER FUNCTIONS ---

def clean_nan(value, default=0):
    if value is None or (isinstance(value, (float, int)) and math.isnan(value)):
        return default
    return value

def get_filtered_data(year, month=None, room_type=None):
    bookings_query = Booking.query.filter(extract('year', Booking.checkin) == year)
    expenses_query = Expense.query.filter(extract('year', Expense.date) == year)

    if month:
        bookings_query = bookings_query.filter(extract('month', Booking.checkin) == month)
        expenses_query = expenses_query.filter(extract('month', Expense.date) == month)

    if room_type and room_type != 'All':
        bookings_query = bookings_query.filter(Booking.unit_name == room_type)
        expenses_query = expenses_query.filter(or_(Expense.unit_name == room_type, Expense.unit_name == None))
    
    return bookings_query.all(), expenses_query.all()

def calculate_dashboard_data(bookings, expenses, year, month, room_type):
    total_booking_revenue = sum(clean_nan(b.total) for b in bookings)
    total_monthly_expenses = sum(clean_nan(e.debit) for e in expenses)
    gross_profit = total_booking_revenue - total_monthly_expenses
    management_fee = gross_profit * 0.30
    monthly_income = gross_profit - management_fee

    if room_type and room_type != 'All':
        room_count = 1
    else:
        room_count = db.session.query(func.count(func.distinct(Booking.unit_name))).scalar() or 1

    days_in_period = calendar.monthrange(year, month)[1] if month else 365
    total_possible_nights = room_count * days_in_period

    total_nights_booked = sum(clean_nan(b.duration, 0) for b in bookings)
    total_occupancy_rate = (total_nights_booked / total_possible_nights) * 100 if total_possible_nights > 0 else 0
    
    summary = {
        'total_booking_revenue': total_booking_revenue,
        'total_monthly_expenses': total_monthly_expenses,
        'gross_profit': gross_profit,
        'management_fee': management_fee,
        'monthly_income': monthly_income,
        'total_occupancy_rate': total_occupancy_rate,
    }

    analysis = {}
    if not month:
        # Use already filtered data for the year, no need to query again
        total_annual_revenue = total_booking_revenue
        total_annual_expenses = total_monthly_expenses
        total_annual_nights = total_nights_booked

        analysis = {
            'total_bookings_count': len(bookings),
            'average_duration': np.mean([clean_nan(b.duration, 0) for b in bookings]) if bookings else 0,
            'average_daily_rate': (total_annual_revenue / total_annual_nights) if total_annual_nights > 0 else 0,
            'revpar': total_annual_revenue / (room_count * 365) if room_count > 0 else 0,
            'average_monthly_revenue': total_annual_revenue / 12,
            'average_monthly_expenses': total_annual_expenses / 12,
        }

    return summary, analysis

# --- AUTH ROUTES ---

@main.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(id=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password', 'danger')
            return redirect(url_for('main.login'))
        login_user(user, remember=form.remember_me.data)
        return redirect(url_for('main.index'))
    return render_template('login.html', title='Sign In', form=form)

@main.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.login'))

# --- CORE APP & CRUD ROUTES ---

@main.route('/')
@login_required
def index():
    try:
        selected_year = request.args.get('year', datetime.now().year, type=int)
        
        years_options = [y[0] for y in db.session.query(extract('year', Booking.checkin)).distinct().order_by(extract('year', Booking.checkin).desc()).all() if y[0]]
        if not years_options: years_options = [selected_year]

        months_options = [{'value': i, 'text': calendar.month_name[i]} for i in range(1, 13)]
        room_types = ['All'] + [r[0] for r in db.session.query(Booking.unit_name).distinct().order_by(Booking.unit_name).all() if r[0]]

        return render_template('index.html',
                               title='Dashboard',
                               years_options=years_options,
                               months_options=months_options,
                               room_types=room_types,
                               default_year=str(selected_year),
                               current_user_role=current_user.role
                               )
    except Exception as e:
        current_app.logger.error(f"Error in index route: {e}")
        return "An internal error occurred.", 500

@main.route('/add_booking', methods=['GET', 'POST'])
@login_required
def add_booking():
    form = BookingForm()
    all_units = [r[0] for r in db.session.query(Booking.unit_name).distinct().order_by(Booking.unit_name).all() if r[0]]
    form.unit_name.choices = all_units
    if form.validate_on_submit():
        new_booking = Booking()
        form.populate_obj(new_booking)
        db.session.add(new_booking)
        db.session.commit()
        flash('新预订已成功添加!', 'success')
        return redirect(url_for('main.index'))
    return render_template('add_booking.html', title='新增预订', form=form, all_units=all_units)

@main.route('/edit_booking/<booking_id>', methods=['GET', 'POST'])
@login_required
def edit_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    form = BookingForm(obj=booking)
    all_units = [r[0] for r in db.session.query(Booking.unit_name).distinct().order_by(Booking.unit_name).all() if r[0]]
    form.unit_name.choices = all_units
    if form.validate_on_submit():
        form.populate_obj(booking)
        db.session.commit()
        flash('预订信息已更新!', 'success')
        return redirect(request.args.get('next') or url_for('main.index'))
    return render_template('edit_booking.html', title='编辑预订', form=form, booking=booking, all_units=all_units)

@main.route('/edit_expense/<expense_id>', methods=['GET', 'POST'])
@login_required
def edit_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    form = ExpenseForm(obj=expense)
    all_units = ['_GENERAL_EXPENSE_'] + [r[0] for r in db.session.query(Booking.unit_name).distinct().order_by(Booking.unit_name).all() if r[0]]
    form.unit_name.choices = all_units
    if form.validate_on_submit():
        form.populate_obj(expense)
        db.session.commit()
        flash('支出信息已更新!', 'success')
        return redirect(request.args.get('next') or url_for('main.index'))
    return render_template('edit_expense.html', title='编辑支出', form=form, expense=expense, all_units=all_units)

# --- PDF DOWNLOAD ROUTE ---

@main.route('/download_monthly_statement')
@login_required
def download_monthly_statement():
    try:
        year = request.args.get('year', datetime.now().year, type=int)
        month = request.args.get('month', datetime.now().month, type=int)
        room_type = request.args.get('room_type', 'All')

        bookings, expenses = get_filtered_data(year, month, room_type)
        summary, _ = calculate_dashboard_data(bookings, expenses, year, month, room_type)
        
        generation_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        rendered_html = render_template('pdf_template.html', 
                                        year=year, month=calendar.month_name[month], room_type=room_type,
                                        summary=summary, bookings=bookings, expenses=expenses,
                                        generation_time=generation_time)
        
        pdf = pdfkit.from_string(rendered_html, False)
        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=monthly_statement_{year}_{month}.pdf'
        return response
    except Exception as e:
        current_app.logger.error(f"Error generating PDF: {e}")
        return "Error generating PDF.", 500

# --- API ROUTES ---

@main.route('/api/filter_data')
@login_required
def api_filter_data():
    try:
        year = request.args.get('year', datetime.now().year, type=int)
        month_str = request.args.get('month', '')
        month = int(month_str) if month_str.isdigit() else None
        room_type = request.args.get('room_type', 'All')
        
        bookings, expenses = get_filtered_data(year, month, room_type)
        summary, analysis = calculate_dashboard_data(bookings, expenses, year, month, room_type)
        
        cleaned_summary = {k: clean_nan(v) for k, v in summary.items()}
        cleaned_analysis = {k: clean_nan(v) for k, v in analysis.items()}

        return jsonify({'summary': cleaned_summary, 'analysis': cleaned_analysis})
    except Exception as e:
        current_app.logger.error(f"Error in /api/filter_data: {e}")
        return jsonify({"error": "Internal server error"}), 500

@main.route('/api/chart_data')
@login_required
def api_chart_data():
    try:
        year = request.args.get('year', datetime.now().year, type=int)
        room_type = request.args.get('room_type', 'All')
        
        monthly_revenue = []
        monthly_expenses = []
        months = [calendar.month_name[i] for i in range(1, 13)]

        for month in range(1, 13):
            bookings, expenses = get_filtered_data(year, month, room_type)
            monthly_revenue.append(sum(clean_nan(b.total) for b in bookings))
            monthly_expenses.append(sum(clean_nan(e.debit) for e in expenses))

        return jsonify({'months': months, 'monthly_revenue': monthly_revenue, 'monthly_expenses': monthly_expenses})
    except Exception as e:
        current_app.logger.error(f"Error in /api/chart_data: {e}")
        return jsonify({"error": "Internal server error"}), 500

@main.route('/api/detailed_data')
@login_required
def api_detailed_data():
    try:
        year = request.args.get('year', datetime.now().year, type=int)
        month_str = request.args.get('month', '')
        month = int(month_str) if month_str.isdigit() else None
        room_type = request.args.get('room_type', 'All')

        bookings, expenses = get_filtered_data(year, month, room_type)
        
        data = []
        for b in bookings:
            data.append({
                'type': 'booking', 'date': b.checkin.strftime('%Y-%m-%d'), 'unit_name': b.unit_name,
                'checkin': b.checkin.strftime('%Y-%m-%d'), 'checkout': b.checkout.strftime('%Y-%m-%d'),
                'channel': b.channel, 'on_offline': b.on_offline, 'pax': b.pax, 'duration': b.duration,
                'price': clean_nan(b.price), 'cleaning_fee': clean_nan(b.cleaning_fee), 
                'platform_charge': clean_nan(b.platform_charge), 'total_booking_revenue': clean_nan(b.total), 
                'booking_number': b.booking_number, 'expense_id': None,
                'additional_expense_category': None, 'additional_expense_amount': 0
            })
        for e in expenses:
            data.append({
                'type': 'expense', 'date': e.date.strftime('%Y-%m-%d'), 'unit_name': e.unit_name or '_GENERAL_EXPENSE_',
                'checkin': '-', 'checkout': '-', 'channel': '-', 'on_offline': '-', 'pax': '-', 'duration': '-',
                'price': 0, 'cleaning_fee': 0, 'platform_charge': 0, 'total_booking_revenue': 0,
                'booking_number': None, 'expense_id': e.id,
                'additional_expense_category': e.particulars, 'additional_expense_amount': clean_nan(e.debit)
            })
        
        data.sort(key=lambda x: x['date'])
        return jsonify({'data': data})
    except Exception as e:
        current_app.logger.error(f"Error in /api/detailed_data: {e}")
        return jsonify({"error": "Internal server error"}), 500