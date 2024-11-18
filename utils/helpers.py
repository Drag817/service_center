# utils/helpers.py
from datetime import datetime
import os
from werkzeug.utils import secure_filename
from PIL import Image

def format_price(price):
    """Форматирует цену с разделителями тысяч"""
    return "{:,.2f}".format(price).replace(',', ' ')

def get_file_extension(filename):
    """Получает расширение файла"""
    return os.path.splitext(filename)[1].lower()

def allowed_file(filename):
    """Проверяет допустимость расширения файла"""
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_image(file, upload_folder, max_size=(800, 800)):
    """Сохраняет и оптимизирует изображение"""
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
        unique_filename = timestamp + filename
        filepath = os.path.join(upload_folder, unique_filename)
        
        # Оптимизация изображения
        img = Image.open(file)
        img.thumbnail(max_size)
        img.save(filepath, optimize=True, quality=85)
        
        return unique_filename
    return None

def get_pagination_range(current_page, total_pages, show_pages=5):
    """Возвращает диапазон страниц для пагинации"""
    half = show_pages // 2
    start_page = max(current_page - half, 1)
    end_page = min(start_page + show_pages - 1, total_pages)
    
    if end_page - start_page + 1 < show_pages:
        start_page = max(end_page - show_pages + 1, 1)
    
    return range(start_page, end_page + 1)

def generate_report_data(data, report_type):
    """Генерирует данные для отчетов"""
    if report_type == 'sales':
        return {
            'labels': [item['date'] for item in data],
            'values': [item['amount'] for item in data],
            'title': 'Отчет по продажам',
            'type': 'line'
        }
    # Добавьте другие типы отчетов при необходимости
    return None
