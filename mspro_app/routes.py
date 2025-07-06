from flask import Blueprint, render_template, request, jsonify, send_file, make_response, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from .extensions import db
from .models import User, Booking, Expense
from .forms import LoginForm, RegistrationForm # Import RegistrationForm
import pandas as pd
import numpy as np
from datetime import datetime
import calendar
from sqlalchemy import extract
from io import BytesIO

main = Blueprint('main', __name__)

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
    selected_month = request.args.get('month', datetime.now().month, type=int)
    
    bookings = Booking.query.filter(
        extract('year', Booking.checkin) == selected_year,
        extract('month', Booking.checkin) == selected_month
    ).all()

    expenses = Expense.query.filter(
        extract('year', Expense.date) == selected_year,
        extract('month', Expense.date) == selected_month
    ).all()

    total_revenue = sum(b.total for b in bookings if b.total)
    total_expense = sum(e.debit for e in expenses if e.debit)
    net_profit = total_revenue - total_expense

    summary = {
        'total_booking_revenue': total_revenue,
        'total_monthly_expenses': total_expense,
        'gross_profit': net_profit,
        'management_fee': net_profit * 0.3,  # Assuming 30% management fee
        'monthly_income': net_profit * 0.7,
        'total_occupancy_rate': 50.0 # Placeholder
    }

    analysis = {
        'total_bookings_count': len(bookings),
        'average_duration': np.mean([b.duration for b in bookings]) if bookings else 0,
        'average_daily_rate': np.mean([b.price for b in bookings]) if bookings else 0,
        'revpar': 0, # Placeholder
        'average_monthly_revenue': total_revenue,
        'average_monthly_expenses': total_expense
    }

    chart_labels = ['January', 'February', 'March', 'April', 'May', 'June']
    chart_revenue = [3000, 4500, 6000, 5500, 7000, 8000]
    chart_expenses = [1500, 2000, 2500, 2300, 3000, 3200]

    return render_template('index.html',
                           title='Dashboard',
                           selected_year=selected_year,
                           selected_month=selected_month,
                           summary=summary,
                           analysis=analysis,
                           years_options=[2023, 2024, 2025], # Placeholder
                           months_options=[{'value': i, 'text': calendar.month_name[i]} for i in range(1, 13)], # Placeholder
                           room_types=['All', 'Room 1', 'Room 2'], # Placeholder
                           default_year=str(selected_year),
                           bookings=bookings,
                           expenses=expenses,
                           chart_labels=chart_labels,
                           chart_revenue=chart_revenue,
                           chart_expenses=chart_expenses)
