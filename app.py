# Файл: service_center_project/app.py
import os
from datetime import datetime

from functools import wraps

from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory


# Создание приложения Flask
app = Flask(__name__)
app.secret_key = '7g8m5SDDy9Nz4PlUbnzQ2WkD4QypIW'  # Замените на свой секретный ключ
app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://root:{app.secret_key}@195.2.78.99:3306/service_center'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max-limit
app.config['CONNECTION_TIMEOUT'] = 86400

# Создаем папку для загрузок, если её нет
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)


# Декораторы для проверки прав доступа
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Необходимо войти в систему.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Необходимо войти в систему.', 'error')
            return redirect(url_for('login'))
        if session.get('role') != 'admin':
            flash('Доступ запрещен. Необходимы права администратора.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)

    return decorated_function


# Проверка расширения файла
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


# Маршрут для отображения загруженных файлов
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# Модели базы данных
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(10), nullable=False, default='user')
    email = db.Column(db.String(120), unique=True)
    phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text)
    image = db.Column(db.String(200))
    popularity = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # Добавляем relationship для получения отзывов
    reviews = db.relationship('Review', backref='product', lazy=True, cascade='all, delete-orphan')


class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'))
    product_id = db.Column(db.Integer, db.ForeignKey('product.id', ondelete='CASCADE'))
    quantity = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # Добавляем relationship для получения информации о продукте
    product = db.relationship('Product', backref='cart_items')


class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'))
    product_id = db.Column(db.Integer, db.ForeignKey('product.id', ondelete='CASCADE'))
    comment = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer, default=5)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # Добавляем relationship для получения информации о пользователе
    user = db.relationship('User', backref='reviews')


# Основные маршруты
@app.route('/')
def index():
    try:
        products = Product.query.order_by(Product.popularity.desc()).limit(6).all()
        # Получаем последние отзывы для главной страницы
        recent_reviews = Review.query.order_by(Review.created_at.desc()).limit(3).all()
        return render_template('index.html',
                               products=products,
                               recent_reviews=recent_reviews,
                               username=session.get('username'),
                               role=session.get('role'))
    except Exception as e:
        print(f"Error: {e}")
        return render_template('index.html',
                               products=[],
                               recent_reviews=[],
                               username=session.get('username'),
                               role=session.get('role'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            username = request.form.get('username')
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')
            role = request.form.get('role', 'user')

            if password != confirm_password:
                flash('Пароли не совпадают!', 'error')
                return redirect(url_for('register'))

            if User.query.filter_by(username=username).first():
                flash('Пользователь с таким именем уже существует!', 'error')
                return redirect(url_for('register'))

            new_user = User(
                username=username,
                password=generate_password_hash(password),
                role=role
            )

            db.session.add(new_user)
            db.session.commit()
            flash('Регистрация успешно завершена!', 'success')
            return redirect(url_for('login'))

        except Exception as e:
            db.session.rollback()
            print(f"Error during registration: {str(e)}")
            flash('Произошла ошибка при регистрации.', 'error')
            return redirect(url_for('register'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            username = request.form.get('username')
            password = request.form.get('password')

            if not username or not password:
                flash('Пожалуйста, заполните все поля!', 'error')
                return redirect(url_for('login'))

            user = User.query.filter_by(username=username).first()

            if user and check_password_hash(user.password, password):
                session['user_id'] = user.id
                session['role'] = user.role
                session['username'] = user.username

                flash(f'Добро пожаловать, {user.username}!', 'success')

                # Направляем пользователя в зависимости от роли
                if user.role == 'admin':
                    return redirect(url_for('admin_panel'))
                else:
                    return redirect(url_for('catalog'))
            else:
                flash('Неверное имя пользователя или пароль!', 'error')

        except Exception as e:
            print(f"Error during login: {str(e)}")
            flash('Произошла ошибка при входе.', 'error')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('Вы успешно вышли из системы.', 'info')
    return redirect(url_for('index'))


@app.route('/catalog')
def catalog():
    try:
        sort_by = request.args.get('sort', 'popularity')
        order = request.args.get('order', 'desc')

        query = Product.query
        if sort_by == 'price':
            if order == 'asc':
                query = query.order_by(Product.price.asc())
            else:
                query = query.order_by(Product.price.desc())
        else:
            query = query.order_by(Product.popularity.desc())

        products = query.all()

        return render_template('catalog.html',
                               products=products,
                               sort_by=sort_by,
                               order=order,
                               username=session.get('username'),
                               role=session.get('role'))
    except Exception as e:
        print(f"Error: {e}")
        flash('Ошибка при загрузке каталога.', 'error')
        return redirect(url_for('index'))


@app.route('/profile')
@login_required
def profile():
    try:
        user = User.query.get_or_404(session['user_id'])
        cart_items = Cart.query.filter_by(user_id=session['user_id']).all()
        reviews = Review.query.filter_by(user_id=session['user_id']).all()

        # Вычисляем общую стоимость корзины
        total_price = sum(item.product.price * item.quantity for item in cart_items)

        return render_template('profile.html',
                               user=user,
                               cart_items=cart_items,
                               reviews=reviews,
                               total_price=total_price,
                               username=session.get('username'),
                               role=session.get('role'))
    except Exception as e:
        flash(f'Ошибка при загрузке профиля: {str(e)}', 'error')
        return redirect(url_for('index'))


@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    try:
        user = User.query.get_or_404(session['user_id'])

        if request.method == 'POST':
            # Обновляем email
            new_email = request.form.get('email')
            if new_email and new_email != user.email:
                if User.query.filter_by(email=new_email).first():
                    flash('Этот email уже используется.', 'error')
                    return redirect(url_for('edit_profile'))
                user.email = new_email

            # Обновляем телефон
            user.phone = request.form.get('phone')

            # Обновляем пароль, если он был предоставлен
            new_password = request.form.get('new_password')
            if new_password:
                user.password = generate_password_hash(new_password)

            db.session.commit()
            flash('Профиль успешно обновлен!', 'success')
            return redirect(url_for('profile'))

    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при обновлении профиля: {str(e)}', 'error')

    return render_template('edit_profile.html',
                           user=user,
                           username=session.get('username'),
                           role=session.get('role'))


@app.route('/cart/add/<int:product_id>', methods=['POST'])
@login_required
def add_to_cart(product_id):
    try:
        product = Product.query.get_or_404(product_id)
        existing_item = Cart.query.filter_by(
            user_id=session['user_id'],
            product_id=product_id
        ).first()

        if existing_item:
            existing_item.quantity += 1
        else:
            cart_item = Cart(user_id=session['user_id'], product_id=product_id)
            db.session.add(cart_item)

        # Увеличиваем популярность товара
        product.popularity += 1

        db.session.commit()
        flash('Услуга добавлена в корзину!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при добавлении в корзину: {str(e)}', 'error')

    return redirect(url_for('catalog'))


@app.route('/cart/remove/<int:cart_id>', methods=['POST'])
@login_required
def remove_from_cart(cart_id):
    try:
        cart_item = Cart.query.get_or_404(cart_id)
        if cart_item.user_id != session['user_id']:
            flash('У вас нет прав для выполнения этого действия.', 'error')
            return redirect(url_for('profile'))

        db.session.delete(cart_item)
        db.session.commit()
        flash('Услуга удалена из корзины.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при удалении из корзины: {str(e)}', 'error')

    return redirect(url_for('profile'))


@app.route('/review/add/<int:product_id>', methods=['POST'])
@login_required
def add_review(product_id):
    try:
        # Проверяем, существует ли уже отзыв от этого пользователя
        existing_review = Review.query.filter_by(
            user_id=session['user_id'],
            product_id=product_id
        ).first()

        if existing_review:
            flash('Вы уже оставили отзыв для этой услуги.', 'error')
            return redirect(url_for('catalog'))

        rating = request.form.get('rating', type=int)
        comment = request.form.get('comment')

        if not rating or not 1 <= rating <= 5:
            flash('Пожалуйста, укажите корректную оценку.', 'error')
            return redirect(url_for('catalog'))

        review = Review(
            user_id=session['user_id'],
            product_id=product_id,
            rating=rating,
            comment=comment
        )

        # Увеличиваем популярность товара при добавлении отзыва
        product = Product.query.get(product_id)
        if product:
            product.popularity += 2

        db.session.add(review)
        db.session.commit()
        flash('Спасибо за ваш отзыв!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при добавлении отзыва: {str(e)}', 'error')

    return redirect(url_for('catalog'))


@app.route('/review/delete/<int:review_id>', methods=['POST'])
@login_required
def delete_review(review_id):
    try:
        review = Review.query.get_or_404(review_id)
        # Проверяем, что отзыв принадлежит текущему пользователю
        if review.user_id != session['user_id'] and session['role'] != 'admin':
            flash('У вас нет прав для удаления этого отзыва.', 'error')
            return redirect(url_for('profile'))

        # Уменьшаем популярность товара при удалении отзыва
        product = Product.query.get(review.product_id)
        if product:
            product.popularity = max(0, product.popularity - 2)

        db.session.delete(review)
        db.session.commit()
        flash('Отзыв успешно удален.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при удалении отзыва: {str(e)}', 'error')

    return redirect(request.referrer or url_for('profile'))


# Административные маршруты
@app.route('/admin')
@admin_required
def admin_panel():
    try:
        products = Product.query.all()
        users = User.query.all()
        reviews = Review.query.all()
        return render_template('admin.html',
                               products=products,
                               users=users,
                               reviews=reviews,
                               username=session.get('username'),
                               role=session.get('role'))
    except Exception as e:
        flash(f'Ошибка при загрузке панели администратора: {str(e)}', 'error')
        return redirect(url_for('index'))


@app.route('/admin/product/add', methods=['GET', 'POST'])
@admin_required
def admin_add_product():
    if request.method == 'POST':
        try:
            name = request.form['name']
            price = float(request.form['price'])
            description = request.form['description']
            file = request.files['image']

            if not name or not price or not description:
                flash('Все поля должны быть заполнены!', 'error')
                return redirect(url_for('admin_add_product'))

            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)

                new_product = Product(
                    name=name,
                    price=price,
                    description=description,
                    image=os.path.join('static/uploads', filename)
                )

                db.session.add(new_product)
                db.session.commit()
                flash('Услуга успешно добавлена!', 'success')
                return redirect(url_for('admin_panel'))
            else:
                flash('Пожалуйста, загрузите изображение в правильном формате.', 'error')
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при добавлении услуги: {str(e)}', 'error')

    return render_template('admin_add_product.html',
                           username=session.get('username'),
                           role=session.get('role'))


@app.route('/admin/product/edit/<int:product_id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_product(product_id):
    try:
        product = Product.query.get_or_404(product_id)

        if request.method == 'POST':
            product.name = request.form['name']
            product.price = float(request.form['price'])
            product.description = request.form['description']

            file = request.files.get('image')
            if file and allowed_file(file.filename):
                # Удаляем старое изображение
                if product.image:
                    old_image_path = os.path.join(app.root_path, product.image)
                    if os.path.exists(old_image_path):
                        os.remove(old_image_path)

                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                product.image = os.path.join('static/uploads', filename)

            db.session.commit()
            flash('Услуга успешно обновлена!', 'success')
            return redirect(url_for('admin_panel'))
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при обновлении услуги: {str(e)}', 'error')

    return render_template('admin_edit_product.html',
                           product=product,
                           username=session.get('username'),
                           role=session.get('role'))


@app.route('/admin/product/delete/<int:product_id>', methods=['POST'])
@admin_required
def admin_delete_product(product_id):
    try:
        product = Product.query.get_or_404(product_id)

        # Удаляем изображение
        if product.image:
            image_path = os.path.join(app.root_path, product.image)
            if os.path.exists(image_path):
                os.remove(image_path)

        db.session.delete(product)
        db.session.commit()
        flash('Услуга успешно удалена.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при удалении услуги: {str(e)}', 'error')

    return redirect(url_for('admin_panel'))


@app.route('/admin/user/add', methods=['GET', 'POST'])
@admin_required
def admin_add_user():
    if request.method == 'POST':
        try:
            username = request.form['username']
            password = request.form['password']
            email = request.form.get('email')
            role = request.form['role']

            if User.query.filter_by(username=username).first():
                flash('Пользователь с таким именем уже существует!', 'error')
                return redirect(url_for('admin_add_user'))

            if email and User.query.filter_by(email=email).first():
                flash('Пользователь с таким email уже существует!', 'error')
                return redirect(url_for('admin_add_user'))

            new_user = User(
                username=username,
                password=generate_password_hash(password),
                email=email,
                role=role
            )

            db.session.add(new_user)
            db.session.commit()
            flash('Пользователь успешно добавлен!', 'success')
            return redirect(url_for('admin_panel'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при добавлении пользователя: {str(e)}', 'error')

    return render_template('admin_add_user.html',
                           username=session.get('username'),
                           role=session.get('role'))


@app.route('/admin/user/edit/<int:user_id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_user(user_id):
    try:
        user = User.query.get_or_404(user_id)

        if request.method == 'POST':
            username = request.form['username']
            email = request.form.get('email')
            role = request.form['role']

            if username != user.username and User.query.filter_by(username=username).first():
                flash('Пользователь с таким именем уже существует!', 'error')
                return redirect(url_for('admin_edit_user', user_id=user_id))

            if email and email != user.email and User.query.filter_by(email=email).first():
                flash('Пользователь с таким email уже существует!', 'error')
                return redirect(url_for('admin_edit_user', user_id=user_id))

            user.username = username
            user.email = email
            user.role = role

            if request.form.get('password'):
                user.password = generate_password_hash(request.form['password'])

            db.session.commit()
            flash('Пользователь успешно обновлен!', 'success')
            return redirect(url_for('admin_panel'))
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при обновлении пользователя: {str(e)}', 'error')

    return render_template('admin_edit_user.html',
                           user=user,
                           username=session.get('username'),
                           role=session.get('role'))


@app.route('/admin/user/delete/<int:user_id>', methods=['POST'])
@admin_required
def admin_delete_user(user_id):
    if user_id == session['user_id']:
        flash('Невозможно удалить собственную учетную запись.', 'error')
        return redirect(url_for('admin_panel'))

    try:
        user = User.query.get_or_404(user_id)
        db.session.delete(user)
        db.session.commit()
        flash('Пользователь успешно удален.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при удалении пользователя: {str(e)}', 'error')

    return redirect(url_for('admin_panel'))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])

    app.run(debug=True, port=3000)
