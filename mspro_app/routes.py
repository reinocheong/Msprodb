from flask import Blueprint, render_template, request, jsonify, send_file, make_response, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from .extensions import db
from .models import User, Booking, Expense
from .forms import LoginForm
import pandas as pd
import numpy as np
from datetime import datetime
import calendar
from sqlalchemy import extract
from io import BytesIO
# import pdfkit # Assuming pdfkit might not be used for now

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

# --- CORE APPLICATION ROUTES ---

@main.route('/')
@login_required
def index():
    """
    Main dashboard view. This is the root URL.
    """
    # Using safe defaults if no query args are provided
    selected_year = request.args.get('year', datetime.now().year, type=int)
    selected_month = request.args.get('month', datetime.now().month, type=int)
    
    # Fetching data - assuming models and columns are correct now
    bookings = Booking.query.filter(
        extract('year', Booking.checkin) == selected_year,
        extract('month', Booking.checkin) == selected_month
    ).all()

    expenses = Expense.query.filter(
        extract('year', Expense.date) == selected_year,
        extract('month', Expense.date) == selected_month
    ).all()

    # This is a placeholder for your complex data calculation logic
    # You would replace this with calls to your helper functions
    total_revenue = sum(b.total for b in bookings if b.total)
    total_expense = sum(e.debit for e in expenses if e.debit)
    net_profit = total_revenue - total_expense

    # Dummy data for charts - replace with your actual data aggregation
    chart_labels = ['January', 'February', 'March', 'April', 'May', 'June']
    chart_revenue = [3000, 4500, 6000, 5500, 7000, 8000]
    chart_expenses = [1500, 2000, 2500, 2300, 3000, 3200]

    return render_template('index.html',
                           title='Dashboard',
                           selected_year=selected_year,
                           selected_month=selected_month,
                           bookings=bookings,
                           expenses=expenses,
                           total_revenue=total_revenue,
                           total_expense=total_expense,
                           net_profit=net_profit,
                           chart_labels=chart_labels,
                           chart_revenue=chart_revenue,
                           chart_expenses=chart_expenses)

# You can add other routes like /admin, /reports etc. here
# For example:
# @main.route('/admin')
# @login_required
# def admin_panel():
#     # Logic for admin panel
#     return render_template('admin.html')