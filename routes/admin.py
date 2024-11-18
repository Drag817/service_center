# routes/admin.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
from functools import wraps

bp = Blueprint('admin', __name__)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Доступ запрещен')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/admin')
@login_required
@admin_required
def dashboard():
    return render_template('admin/dashboard.html')

@bp.route('/admin/services', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_services():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        price = request.form.get('price')
        image = request.files.get('image')
        
        if image:
            filename = secure_filename(image.filename)
            image.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
        else:
            filename = 'default.jpg'
        
        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO services (name, description, price, image_path)
            VALUES (%s, %s, %s, %s)
        """, (name, description, price, filename))
        
        mysql.connection.commit()
        cur.close()
        
        flash('Услуга успешно добавлена')
        return redirect(url_for('admin.manage_services'))
    
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM services")
    services = cur.fetchall()
    cur.close()
    
    return render_template('admin/services.html', services=services)

@bp.route('/admin/users')
@login_required
@admin_required
def manage_users():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM users")
    users = cur.fetchall()
    cur.close()
    
    return render_template('admin/users.html', users=users)

@bp.route('/admin/reports')
@login_required
@admin_required
def reports():
    cur = mysql.connection.cursor()
    
    # Статистика по заказам
    cur.execute("""
        SELECT 
            COUNT(*) as total_orders,
            SUM(total_amount) as total_revenue,
            AVG(total_amount) as avg_order_value
        FROM orders
    """)
    order_stats = cur.fetchone()
    
    # Топ услуг
    cur.execute("""
        SELECT 
            s.name,
            COUNT(oi.id) as times_ordered,
            SUM(oi.quantity) as total_quantity
        FROM services s
        LEFT JOIN order_items oi ON s.id = oi.service_id
        GROUP BY s.id
        ORDER BY times_ordered DESC
        LIMIT 5
    """)
    top_services = cur.fetchall()
    
    cur.close()
    
    return render_template('admin/reports.html',
                         order_stats=order_stats,
                         top_services=top_services)