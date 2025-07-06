from flask import Blueprint, render_template, request, jsonify, send_file, make_response, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from .extensions import db
from .models import User, Booking, Expense
from .forms import LoginForm, RegistrationForm
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import calendar
from sqlalchemy import extract, func, and_, or_
import math
import pdfkit

main = Blueprint('main', __name__)

# --- HELPER FUNCTIONS ---

def clean_nan(value, default=0):
    """Converts NaN or None to a default value (0 for numbers), otherwise returns value."""
    if value is None or (isinstance(value, (int, float)) and math.isnan(value)):
        return default
    return value

def get_filtered_data(year, month=None, room_type=None):
    # --- BOOKINGS ---
    bookings_query = Booking.query
    if year:
        bookings_query = bookings_query.filter(extract('year', Booking.checkin) == year)
    if month:
        bookings_query = bookings_query.filter(extract('month', Booking.checkin) == month)
    if room_type and room_type != 'All':
        bookings_query = bookings_query.filter(Booking.unit_name == room_type)

    # --- EXPENSES ---
    expenses_query = Expense.query
    if year:
        expenses_query = expenses_query.filter(extract('year', Expense.date) == year)
    if month:
        expenses_query = expenses_query.filter(extract('month', Expense.date) == month)
    
    if room_type and room_type != 'All':
        expenses_query = expenses_query.filter(
            or_(
                Expense.unit_name == room_type,
                Expense.unit_name == None
            )
        )
    
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

    if month:
        days_in_month = calendar.monthrange(year, month)[1]
        total_possible_nights = room_count * days_in_month
    else:
        total_possible_nights = room_count * 365

    total_nights_booked = sum(clean_nan(b.duration, default=0) for b in bookings)
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
        all_bookings_this_year = Booking.query.filter(extract('year', Booking.checkin) == year).all()
        all_expenses_this_year = Expense.query.filter(extract('year', Expense.date) == year).all()
        
        total_annual_revenue = sum(clean_nan(b.total) for b in all_bookings_this_year)
        total_annual_expenses = sum(clean_nan(e.debit) for e in all_expenses_this_year)
        total_annual_nights = sum(clean_nan(b.duration, default=0) for b in all_bookings_this_year)

        analysis = {
            'total_bookings_count': len(all_bookings_this_year),
            'average_duration': np.mean([clean_nan(b.duration, 0) for b in all_bookings_this_year]) if all_bookings_this_year else 0,
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

# --- CORE APP ROUTES ---

@main.route('/')
@login_required
def index():
    selected_year = request.args.get('year', datetime.now().year, type=int)
    selected_month_str = request.args.get('month', '')
    selected_month = int(selected_month_str) if selected_month_str.isdigit() else None
    selected_room_type = request.args.get('room_type', 'All')

    bookings, expenses = get_filtered_data(selected_year, selected_month, selected_room_type)
    summary, analysis = calculate_dashboard_data(bookings, expenses, selected_year, selected_month, selected_room_type)

    years_options = [y[0] for y in db.session.query(extract('year', Booking.checkin)).distinct().order_by(extract('year', Booking.checkin).desc()).all() if y[0]]
    months_options = [{'value': i, 'text': calendar.month_name[i]} for i in range(1, 13)]
    room_types = ['All'] + [r[0] for r in db.session.query(Booking.unit_name).distinct().order_by(Booking.unit_name).all() if r[0]]

    return render_template('index.html',
                           title='Dashboard',
                           summary=summary,
                           analysis=analysis,
                           years_options=years_options,
                           months_options=months_options,
                           room_types=room_types,
                           default_year=str(selected_year),
                           current_user_role=current_user.role
                           )

# --- PDF DOWNLOAD ROUTE ---

@main.route('/download_monthly_statement')
@login_required
def download_monthly_statement():
    year = request.args.get('year', datetime.now().year, type=int)
    month = request.args.get('month', datetime.now().month, type=int)
    room_type = request.args.get('room_type', 'All')

    bookings, expenses = get_filtered_data(year, month, room_type)
    summary, _ = calculate_dashboard_data(bookings, expenses, year, month, room_type)

    # Render HTML template for PDF
    rendered_html = render_template('pdf_template.html', 
                                    year=year, 
                                    month=calendar.month_name[month], 
                                    room_type=room_type,
                                    summary=summary,
                                    bookings=bookings,
                                    expenses=expenses)
    
    # Generate PDF from HTML
    # Note: You might need to configure the path to wkhtmltopdf on your system
    # For Render, you might need a buildpack or specify the path in your Dockerfile
    try:
        pdf = pdfkit.from_string(rendered_html, False)
    except OSError as e:
        # This can happen if wkhtmltopdf is not found
        return f"Error generating PDF: {e}. Ensure wkhtmltopdf is installed and in your system's PATH.", 500


    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=monthly_statement_{year}_{month}.pdf'
    
    return response

# --- API ROUTES ---

@main.route('/api/filter_data', methods=['GET'])
@login_required
def api_filter_data():
    year = request.args.get('year', datetime.now().year, type=int)
    month_str = request.args.get('month', '')
    month = int(month_str) if month_str.isdigit() else None
    room_type = request.args.get('room_type', 'All')
    
    bookings, expenses = get_filtered_data(year, month, room_type)
    summary, analysis = calculate_dashboard_data(bookings, expenses, year, month, room_type)
    
    cleaned_summary = {k: clean_nan(v) for k, v in summary.items()}
    cleaned_analysis = {k: clean_nan(v) for k, v in analysis.items()}

    return jsonify({'summary': cleaned_summary, 'analysis': cleaned_analysis})

@main.route('/api/chart_data', methods=['GET'])
@login_required
def api_chart_data():
    year = request.args.get('year', datetime.now().year, type=int)
    room_type = request.args.get('room_type', 'All')
    
    monthly_revenue = []
    monthly_expenses = []
    months = [calendar.month_name[i] for i in range(1, 13)]

    for month in range(1, 13):
        bookings, expenses = get_filtered_data(year, month, room_type)
        monthly_revenue.append(sum(clean_nan(b.total) for b in bookings))
        monthly_expenses.append(sum(clean_nan(e.debit) for e in expenses))

    return jsonify({
        'months': months,
        'monthly_revenue': monthly_revenue,
        'monthly_expenses': monthly_expenses
    })

@main.route('/api/detailed_data', methods=['GET'])
@login_required
def api_detailed_data():
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
