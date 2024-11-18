# routes/catalog.py
from flask import Blueprint, render_template, request, current_app
from models.service import Service
import math

bp = Blueprint('catalog', __name__)

@bp.route('/services')
def services():
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['ITEMS_PER_PAGE']
    
    cur = mysql.connection.cursor()
    
    # Получаем общее количество услуг
    cur.execute("SELECT COUNT(*) FROM services")
    total_services = cur.fetchone()[0]
    
    # Вычисляем общее количество страниц
    total_pages = math.ceil(total_services / per_page)
    
    # Получаем услуги для текущей страницы
    offset = (page - 1) * per_page
    cur.execute("""
        SELECT id, name, description, price, image_path 
        FROM services 
        LIMIT %s OFFSET %s
    """, (per_page, offset))
    
    services = [
        {
            'id': row[0],
            'name': row[1],
            'description': row[2],
            'price': row[3],
            'image_path': row[4]
        }
        for row in cur.fetchall()
    ]
    cur.close()
    
    return render_template('catalog/services.html',
                         services=services,
                         page=page,
                         total_pages=total_pages)

@bp.route('/service/<int:service_id>')
def service_detail(service_id):
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT id, name, description, price, image_path 
        FROM services 
        WHERE id = %s
    """, (service_id,))
    
    service = cur.fetchone()
    cur.close()
    
    if service:
        service_data = {
            'id': service[0],
            'name': service[1],
            'description': service[2],
            'price': service[3],
            'image_path': service[4]
        }
        return render_template('catalog/service.html', service=service_data)
    return render_template('404.html'), 404