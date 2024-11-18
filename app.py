from flask import Flask, render_template, flash, redirect, url_for, request, session, jsonify
from flask_login import LoginManager, current_user, login_required, login_user, logout_user
import pymysql
from datetime import datetime, timedelta
import secrets
import os
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

# Инициализация Flask приложения
app = Flask(__name__)

# Конфигурация приложения
app.config.update(
    SECRET_KEY=secrets.token_hex(16),
    UPLOAD_FOLDER=os.path.join('static', 'images', 'services'),
    MAX_CONTENT_LENGTH=16 * 1024 * 1024,
    PERMANENT_SESSION_LIFETIME=timedelta(days=7)
)

connection = pymysql.connect(
            host="mysql_db",
            port=3306,
            user=os.getenv("MYSQL_USER"),
            password=os.getenv("MYSQL_PASS"),
            database="service_center",
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )

# Инициализация Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Пожалуйста, войдите для доступа к этой странице.'
login_manager.login_message_category = 'warning'


class User:
    def __init__(self, id, username, email, role):
        self.id = id
        self.username = username
        self.email = email
        self.role = role
        self.is_active = True
        self.is_authenticated = True
        self.is_anonymous = False

    def get_id(self):
        return str(self.id)

    @property
    def is_admin(self):
        return self.role == 'admin'


@login_manager.user_loader
def load_user(user_id):
    # with connection:
    with connection.cursor() as cur:
        cur.execute("SELECT id, username, email, role FROM users WHERE id = %s", (user_id,))
        user_data = cur.fetchone()

    if user_data:
        return User(
            user_data['id'],
            user_data['username'],
            user_data['email'],
            user_data['role']
        )
    else:
        return None


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Пожалуйста, войдите в систему', 'error')

            return redirect(url_for('login'))

        if not current_user.is_admin:
            flash('Доступ запрещен. Необходимы права администратора.', 'error')

            return redirect(url_for('index'))

        return f(*args, **kwargs)

    return decorated_function


def get_cart_data():
    cart = session.get('cart', {})

    if not cart:
        return [], 0

    # cur = connection.cursor()
    total = 0
    items = []

    # with connection:
    with connection.cursor() as cur:
        for service_id, quantity in cart.items():
            cur.execute("""
                SELECT id, name, price, image_path 
                FROM services 
                WHERE id = %s
            """, (service_id,))
            service = cur.fetchone()

            if service:
                item_total = float(service['price']) * quantity
                items.append({
                    'id': service['id'],
                    'name': service['name'],
                    'price': float(service['price']),
                    'image_path': service['image_path'],
                    'quantity': quantity,
                    'total': item_total
                })
                total += item_total

    return items, total


# Маршруты
@app.route('/')
def index():
    try:
        # Популярные услуги
        # with connection:
        with connection.cursor() as cur:
            cur.execute("""
                SELECT s.*, COUNT(oi.id) as orders_count
                FROM services s
                LEFT JOIN order_items oi ON s.id = oi.service_id
                GROUP BY s.id
                ORDER BY orders_count DESC, s.created_at DESC
                LIMIT 6
            """)
            popular_services = cur.fetchall()

            # Статистика
            cur.execute("SELECT COUNT(*) as count FROM orders WHERE status = 'completed'")
            completed_orders = cur.fetchone()['count']

            cur.execute("SELECT COUNT(*) as count FROM users WHERE role = 'user'")
            total_clients = cur.fetchone()['count']

        return render_template(
            'index.html',
            popular_services=popular_services,
            completed_orders=completed_orders,
            total_clients=total_clients,
            avg_rating=4.5
        )

    except Exception as e:
        print(f"Error in index: {e}")
        flash('Произошла ошибка при загрузке данных', 'error')

        return render_template(
            'index.html',
            popular_services=[],
            completed_orders=0,
            total_clients=0,
            avg_rating=0
        )
    # finally:
    #     cur.close()


@app.route('/services')
def services():
    page = request.args.get('page', 1, type=int)
    per_page = 9

    # with connection:
    with connection.cursor() as cur:
        # Получаем общее количество услуг
        cur.execute("SELECT COUNT(*) as count FROM services")
        total_services = cur.fetchone()['count']

        # Получаем услуги для текущей страницы
        offset = (page - 1) * per_page

    # connection.ping()
    with connection.cursor() as cur:
        cur.execute("""
            SELECT id, name, description, price, image_path
            FROM services
            LIMIT %s OFFSET %s
        """, (per_page, offset))

        services = cur.fetchall()

    return render_template('catalog/services.html',
        services=services,
        page=page,
        total_pages=(total_services + per_page - 1) // per_page)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # with connection:
        with connection.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE username = %s", (username,))
            user = cur.fetchone()

        if user and check_password_hash(user['password_hash'], password):
            user_obj = User(
                id=user['id'],
                username=user['username'],
                email=user['email'],
                role=user['role']
            )
            login_user(user_obj)
            flash('Вы успешно вошли в систему!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page if next_page else url_for('index'))

        flash('Неверное имя пользователя или пароль', 'error')

    return render_template('auth/login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not all([username, email, password]):
            flash('Все поля должны быть заполнены', 'error')
            return render_template('auth/register.html')

        try:
            # with connection:
            with connection.cursor() as cur:
                # Проверяем существование пользователя
                cur.execute("SELECT id FROM users WHERE username = %s OR email = %s",
                           (username, email))
                if cur.fetchone():
                    flash('Пользователь с таким именем или email уже существует', 'error')
                    return render_template('auth/register.html')

                # Создаем пользователя
                password_hash = generate_password_hash(password)
                cur.execute("""
                    INSERT INTO users (username, email, password_hash, role)
                    VALUES (%s, %s, %s, 'user')
                """, (username, email, password_hash))
                connection.commit()

                flash('Регистрация успешна! Теперь вы можете войти', 'success')

            return redirect(url_for('login'))

        except Exception as e:
            connection.rollback()
            print(f"Registration error: {e}")
            flash('Произошла ошибка при регистрации', 'error')

    return render_template('auth/register.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы успешно вышли из системы', 'success')
    return redirect(url_for('index'))


@app.route('/cart')
@login_required
def cart():
    items, total = get_cart_data()

    return render_template(
        'cart/cart.html',
        items=items,
        total=total
    )


@app.route('/cart/add/<int:service_id>', methods=['POST'])
@login_required
def add_to_cart(service_id):
    quantity = int(request.form.get('quantity', 1))
    cart = session.get('cart', {})

    # with connection:
    with connection.cursor() as cur:
        cur.execute("SELECT id FROM services WHERE id = %s", (service_id,))
        if not cur.fetchone():
            flash('Услуга не найдена', 'error')
            return redirect(url_for('services'))

        cart[str(service_id)] = cart.get(str(service_id), 0) + quantity
        session['cart'] = cart
        flash('Услуга добавлена в корзину', 'success')

    return redirect(url_for('services'))


@app.route('/cart/remove/<int:service_id>', methods=['POST'])
@login_required
def remove_from_cart(service_id):
    cart = session.get('cart', {})
    if str(service_id) in cart:
        del cart[str(service_id)]
        session['cart'] = cart
        flash('Услуга удалена из корзины', 'success')

    return redirect(url_for('cart'))


@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    # with connection:
    with connection.cursor() as cur:
        # Статистика
        cur.execute("SELECT COUNT(*) as count FROM users WHERE role = 'user'")
        users_count = cur.fetchone()['count']

        cur.execute("SELECT COUNT(*) as count FROM orders WHERE status = 'pending'")
        pending_orders = cur.fetchone()['count']

        cur.execute("""
            SELECT SUM(total_amount) as revenue
            FROM orders
            WHERE status = 'completed'
            AND created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
        """)
        monthly_revenue = cur.fetchone()['revenue'] or 0

        # Последние заказы
        cur.execute("""
            SELECT o.*, u.username
            FROM orders o
            JOIN users u ON o.user_id = u.id
            ORDER BY o.created_at DESC
            LIMIT 5
        """)
        recent_orders = cur.fetchall()

    return render_template(
        'admin/dashboard.html',
        users_count=users_count,
        pending_orders=pending_orders,
        monthly_revenue=monthly_revenue,
        recent_orders=recent_orders
    )


@app.route('/admin/services')
@login_required
@admin_required
def admin_services():
    # with connection:
    with connection.cursor() as cur:
        cur.execute("SELECT * FROM services ORDER BY created_at DESC")
        services = cur.fetchall()

    return render_template('admin/services.html', services=services)


# Контекстный процессор
@app.context_processor
def utility_processor():
    def format_price(amount):
        if amount is None:
            return "0.00"
        return "{:,.2f}".format(float(amount)).replace(',', ' ')

    def get_cart_count():
        return sum(session.get('cart', {}).values())

    return dict(
        format_price=format_price,
        get_cart_count=get_cart_count,
        now=datetime.now()
    )


def init_db():
    with app.app_context():
        # try:
        # with connection:
        with connection.cursor() as cur:
            # Создание таблиц
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    email VARCHAR(100) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    role ENUM('admin', 'user') DEFAULT 'user',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS services (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    name VARCHAR(100) NOT NULL,
                    description TEXT,
                    price DECIMAL(10, 2) NOT NULL,
                    image_path VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    user_id INT,
                    total_amount DECIMAL(10, 2) NOT NULL,
                    status ENUM('pending', 'confirmed', 'completed', 'cancelled') DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS order_items (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    order_id INT,
                    service_id INT,
                    quantity INT NOT NULL,
                    price DECIMAL(10, 2) NOT NULL,
                    FOREIGN KEY (order_id) REFERENCES orders(id),
                    FOREIGN KEY (service_id) REFERENCES services(id)
                )
            """)

            # Создание администратора по умолчанию
            admin_password = generate_password_hash(os.getenv('PORTAL_ADMIN_PASSWORD'))

            try:
                cur.execute("""
                    INSERT INTO users (username, email, password_hash, role)
                    VALUES (%s, %s, %s, %s)
                """, (os.getenv('PORTAL_ADMIN_LOGIN'), 'admin@example.com', admin_password, 'admin'))
                connection.commit()
                print("Admin user created successfully")

            except Exception as e:
                print(f"Admin user already exists: {e}")
                
        # except Exception as e:
        #     print(f"Database initialization error: {e}")
        #     connection.rollback()

        # finally:
        #     connection.close()


if __name__ == '__main__':
    # Инициализация базы данных
    init_db()
    #
    # Создаем папку для загрузки изображений
    # os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    # print("Starting application...")
    #
    # Запускаем приложение
    app.run(debug=True, host='0.0.0.0', port=3000)
