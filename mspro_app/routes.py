from flask import Blueprint, render_template, request, jsonify, make_response, redirect, url_for, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from .extensions import db
from .models import User, Booking, Expense
from .forms import LoginForm, RegistrationForm, BookingForm, ExpenseForm, PasswordResetForm, ChangePasswordForm
import pandas as pd
import numpy as np
from datetime import datetime
import calendar
from sqlalchemy import extract, func, or_
import math
import pdfkit
import logging

logging.basicConfig(level=logging.INFO)
main = Blueprint('main', __name__)

def clean_nan(value, default=0):
    if value is None or (isinstance(value, (float, int)) and math.isnan(value)):
        return default
    return value

def get_filtered_data(year, month=None, room_type=None):
    bookings_query = Booking.query
    expenses_query = Expense.query

    if current_user.is_authenticated and current_user.role == 'owner':
        allowed_units = current_user.allowed_units or []
        bookings_query = bookings_query.filter(Booking.unit_name.in_(allowed_units))
        expenses_query = expenses_query.filter(
            or_(Expense.unit_name.in_(allowed_units), Expense.unit_name.is_(None), Expense.unit_name == '')
        )

    if year:
        bookings_query = bookings_query.filter(extract('year', Booking.checkin) == year)
        expenses_query = expenses_query.filter(extract('year', Expense.date) == year)
    if month:
        bookings_query = bookings_query.filter(extract('month', Booking.checkin) == month)
        expenses_query = expenses_query.filter(extract('month', Expense.date) == month)

    if room_type and room_type != 'All':
        if current_user.is_authenticated and current_user.role == 'owner':
            if room_type in current_user.allowed_units:
                bookings_query = bookings_query.filter(Booking.unit_name == room_type)
                expenses_query = expenses_query.filter(or_(Expense.unit_name == room_type, Expense.unit_name.is_(None)))
        else:
            bookings_query = bookings_query.filter(Booking.unit_name == room_type)
            expenses_query = expenses_query.filter(or_(Expense.unit_name == room_type, Expense.unit_name.is_(None)))

    return bookings_query.all(), expenses_query.all()

def calculate_dashboard_data(bookings, expenses, year, month, room_type):
    total_booking_revenue = sum(clean_nan(b.total) for b in bookings)
    total_monthly_expenses = sum(clean_nan(e.debit) for e in expenses)
    gross_profit = total_booking_revenue - total_monthly_expenses
    
    fee_rate = 30.0
    if current_user.is_authenticated:
        user_fee = getattr(current_user, 'management_fee_percentage', 30.0)
        if user_fee is not None:
            fee_rate = user_fee
            
    management_fee = gross_profit * (fee_rate / 100.0)
    monthly_income = gross_profit - management_fee

    if room_type and room_type != 'All':
        room_count = 1
    else:
        if current_user.is_authenticated and current_user.role == 'owner':
            room_count = len(current_user.allowed_units or [])
        else:
            room_count = db.session.query(func.count(func.distinct(Booking.unit_name))).scalar()
    
    room_count = room_count or 1

    days_in_period = calendar.monthrange(year, month)[1] if month else 365
    total_possible_nights = room_count * days_in_period
    total_nights_booked = sum(clean_nan(b.duration, 0) for b in bookings)
    total_occupancy_rate = (total_nights_booked / total_possible_nights) * 100 if total_possible_nights > 0 else 0
    
    revpar = total_booking_revenue / total_possible_nights if total_possible_nights > 0 else 0

    summary = {
        'total_booking_revenue': total_booking_revenue, 'total_monthly_expenses': total_monthly_expenses,
        'gross_profit': gross_profit, 'management_fee': management_fee, 'fee_rate': fee_rate,
        'monthly_income': monthly_income, 'total_occupancy_rate': total_occupancy_rate,
        'revpar': revpar
    }
    return summary, {}

@main.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated: return redirect(url_for('main.index'))
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

@main.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated: return redirect(url_for('main.index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(id=form.username.data); user.set_password(form.password.data)
        db.session.add(user); db.session.commit()
        flash('Congratulations, you are now a registered user!', 'success')
        return redirect(url_for('main.login'))
    return render_template('register.html', title='Register', form=form)

@main.route('/')
@login_required
def index():
    try:
        selected_year = request.args.get('year', datetime.now().year, type=int)
        
        years_query = db.session.query(extract('year', Booking.checkin)).distinct()
        if current_user.role == 'owner':
            years_query = years_query.filter(Booking.unit_name.in_(current_user.allowed_units or []))
        years_options = [y[0] for y in years_query.order_by(extract('year', Booking.checkin).desc()).all() if y[0]]
        
        if not years_options: years_options = [datetime.now().year]
        if selected_year not in years_options: selected_year = years_options[0]
        
        months_options = [{'value': i, 'text': calendar.month_name[i]} for i in range(1, 13)]
        
        if current_user.role == 'admin':
            room_types = ['All'] + [r[0] for r in db.session.query(Booking.unit_name).distinct().order_by(Booking.unit_name).all() if r[0]]
        else:
            room_types = ['All'] + (current_user.allowed_units or [])
            
        return render_template('index.html', title='Dashboard', years_options=years_options, months_options=months_options, room_types=room_types, default_year=str(selected_year), current_user_role=current_user.role)
    except Exception as e:
        current_app.logger.error(f"Error in index route: {e}"); return "An internal error occurred.", 500

@main.route('/download_monthly_statement')
@login_required
def download_monthly_statement():
    try:
        year = request.args.get('year', datetime.now().year, type=int)
        month = request.args.get('month', type=int)
        if not month:
            flash('请选择一个月份来生成月结单。', 'warning')
            return redirect(url_for('main.index'))
        room_type = request.args.get('room_type', 'All')
        bookings, expenses = get_filtered_data(year, month, room_type)
        summary, _ = calculate_dashboard_data(bookings, expenses, year, month, room_type)
        generation_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        rendered_html = render_template('pdf_template.html', year=year, month=calendar.month_name[month], room_type=room_type, summary=summary, bookings=bookings, expenses=expenses, generation_time=generation_time)
        pdf = pdfkit.from_string(rendered_html, False)
        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=monthly_statement_{year}_{month}.pdf'
        return response
    except Exception as e:
        current_app.logger.error(f"Error generating PDF: {e}"); return "Error generating PDF.", 500

@main.route('/api/filter_data')
@login_required
def api_filter_data():
    try:
        year = request.args.get('year', datetime.now().year, type=int)
        month_str = request.args.get('month', ''); month = int(month_str) if month_str.isdigit() else None
        room_type = request.args.get('room_type', 'All')
        bookings, expenses = get_filtered_data(year, month, room_type)
        summary, analysis = calculate_dashboard_data(bookings, expenses, year, month, room_type)
        return jsonify({'summary': {k: clean_nan(v) for k, v in summary.items()}, 'analysis': {k: clean_nan(v) for k, v in analysis.items()}})
    except Exception as e:
        current_app.logger.error(f"Error in /api/filter_data: {e}"); return jsonify({"error": "Internal server error"}), 500

@main.route('/api/chart_data')
@login_required
def api_chart_data():
    try:
        year = request.args.get('year', datetime.now().year, type=int)
        compare_year_str = request.args.get('compare_year', '')
        compare_year = int(compare_year_str) if compare_year_str.isdigit() else None
        room_type = request.args.get('room_type', 'All')

        def get_monthly_data(target_year):
            revenue, expenses, cleaning_fees = [], [], []
            for month in range(1, 13):
                bookings, expense_items = get_filtered_data(target_year, month, room_type)
                revenue.append(sum(clean_nan(b.total) for b in bookings))
                expenses.append(sum(clean_nan(e.debit) for e in expense_items))
                cleaning_fees.append(sum(clean_nan(b.cleaning_fee) for b in bookings))
            return revenue, expenses, cleaning_fees

        main_revenue, main_expenses, main_cleaning_fees = get_monthly_data(year)
        
        response = {
            'months': calendar.month_name[1:],
            'main_year': {'year': year, 'revenue': main_revenue, 'expenses': main_expenses, 'cleaning_fees': main_cleaning_fees}
        }

        if compare_year:
            compare_revenue, _, _ = get_monthly_data(compare_year)
            response['compare_year'] = {'year': compare_year, 'revenue': compare_revenue}
            
        return jsonify(response)
    except Exception as e:
        current_app.logger.error(f"Error in /api/chart_data: {e}"); return jsonify({"error": "Internal server error"}), 500

@main.route('/api/revenue_by_channel')
@login_required
def api_revenue_by_channel():
    try:
        year = request.args.get('year', datetime.now().year, type=int)
        room_type = request.args.get('room_type', 'All')

        query = db.session.query(
            Booking.channel,
            func.sum(Booking.total)
        ).filter(extract('year', Booking.checkin) == year)
        
        if current_user.role == 'owner':
            query = query.filter(Booking.unit_name.in_(current_user.allowed_units or []))
        
        if room_type and room_type != 'All':
            query = query.filter(Booking.unit_name == room_type)
            
        channel_revenue = query.group_by(Booking.channel).order_by(func.sum(Booking.total).desc()).all()

        labels = [item[0] or "Unknown" for item in channel_revenue]
        values = [clean_nan(item[1]) for item in channel_revenue]
        
        return jsonify({'labels': labels, 'values': values})
    except Exception as e:
        current_app.logger.error(f"Error in /api/revenue_by_channel: {e}"); return jsonify({"error": "Internal server error"}), 500

@main.route('/api/detailed_data')
@login_required
def api_detailed_data():
    try:
        year = request.args.get('year', datetime.now().year, type=int)
        month_str = request.args.get('month', ''); month = int(month_str) if month_str.isdigit() else None
        room_type = request.args.get('room_type', 'All')
        bookings, expenses = get_filtered_data(year, month, room_type)
        
        data = []
        for b in bookings:
            booking_data = {
                'type': 'booking', 'id': b.id, 'date': b.checkin.strftime('%Y-%m-%d'),
                'unit_name': b.unit_name,
                'checkin': b.checkin.strftime('%Y-%m-%d'), 'checkout': b.checkout.strftime('%Y-%m-%d'),
                'channel': b.channel, 'on_offline': b.on_offline, 'pax': b.pax, 'duration': b.duration,
                'price': clean_nan(b.price), 'cleaning_fee': clean_nan(b.cleaning_fee), 
                'platform_charge': clean_nan(b.platform_charge), 'total_booking_revenue': clean_nan(b.total), 
                'booking_number': str(b.booking_number) if b.booking_number else '-',
                'additional_expense_category': '-', 
                'additional_expense_amount': 0
            }
            data.append(booking_data)

        for e in expenses:
            expense_data = {
                'type': 'expense', 'id': e.id, 'date': e.date.strftime('%Y-%m-%d'),
                'unit_name': e.unit_name or '_GENERAL_EXPENSE_',
                'checkin': '-', 'checkout': '-', 'channel': '-', 'on_offline': '-', 'pax': '-', 'duration': '-',
                'price': 0, 'cleaning_fee': 0, 'platform_charge': 0, 'total_booking_revenue': 0,
                'booking_number': '-',
                'additional_expense_category': e.particulars, 
                'additional_expense_amount': clean_nan(e.debit)
            }
            data.append(expense_data)

        data.sort(key=lambda x: x['date']); 
        return jsonify({'data': data})
    except Exception as e:
        current_app.logger.error(f"Error in /api/detailed_data: {e}"); 
        return jsonify({"error": "Internal server error"}), 500


@main.route('/admin')
@login_required
def admin():
    if current_user.role != 'admin':
        flash('您没有权限访问此页面。', 'danger')
        return redirect(url_for('main.index'))
    
    users = User.query.order_by(User.id).all()
    all_units = sorted([r[0] for r in db.session.query(Booking.unit_name).distinct().all() if r[0]])
    
    return render_template('admin.html', title='管理面板', users=users, all_units=all_units)

@main.route('/api/update_user_permissions', methods=['POST'])
@login_required
def update_user_permissions():
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': '权限不足'}), 403
    
    data = request.get_json()
    user_id = data.get('user_id')
    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'message': '用户未找到'}), 404

    if 'allowed_units' in data:
        user.allowed_units = data.get('allowed_units', [])
    
    if 'management_fee_percentage' in data:
        try:
            fee = float(data['management_fee_percentage'])
            if 0 <= fee <= 100:
                user.management_fee_percentage = fee
            else:
                return jsonify({'success': False, 'message': '管理费率必须在0到100之间'}), 400
        except (ValueError, TypeError):
            return jsonify({'success': False, 'message': '无效的管理费率格式'}), 400
            
    db.session.commit()
    
    return jsonify({'success': True, 'message': '用户资料已更新'})

@main.route('/request_password_reset/<user_id>', methods=['POST'])
@login_required
def request_password_reset(user_id):
    if current_user.role != 'admin':
        flash('您没有权限执行此操作。', 'danger')
        return redirect(url_for('main.admin'))
    
    user = User.query.get_or_404(user_id)
    token = user.get_reset_password_token()
    reset_url = url_for('main.reset_password', token=token, _external=True)
    
    flash(f'请将此链接发送给用户以重置密码 (30分钟内有效): {reset_url}', 'info')
    return redirect(url_for('main.admin'))

@main.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user = User.verify_reset_password_token(token)
    if not user:
        flash('无效或已过期的重置链接。', 'warning')
        return redirect(url_for('main.login'))
    
    form = PasswordResetForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('您的密码已成功重置！现在可以登录了。', 'success')
        return redirect(url_for('main.login'))
        
    return render_template('reset_password.html', title='重置密码', form=form)

@main.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash('当前密码不正确，请重试。', 'danger')
            return redirect(url_for('main.change_password'))
        
        current_user.set_password(form.new_password.data)
        db.session.commit()
        flash('您的密码已成功修改！', 'success')
        return redirect(url_for('main.index'))
        
    return render_template('change_password.html', title='修改密码', form=form)