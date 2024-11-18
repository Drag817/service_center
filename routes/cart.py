# routes/cart.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_required, current_user

bp = Blueprint('cart', __name__)

@bp.route('/cart')
@login_required
def view():
    cart = session.get('cart', {})
    
    if not cart:
        return render_template('cart/cart.html', items=[], total=0)
    
    cur = mysql.connection.cursor()
    items = []
    total = 0
    
    for service_id, quantity in cart.items():
        cur.execute("""
            SELECT id, name, price, image_path 
            FROM services 
            WHERE id = %s
        """, (service_id,))
        
        service = cur.fetchone()
        if service:
            item_total = service[2] * quantity
            items.append({
                'id': service[0],
                'name': service[1],
                'price': service[2],
                'quantity': quantity,
                'total': item_total,
                'image_path': service[3]
            })
            total += item_total
    
    cur.close()
    return render_template('cart/cart.html', items=items, total=total)

@bp.route('/cart/add/<int:service_id>', methods=['POST'])
@login_required
def add_to_cart(service_id):
    cart = session.get('cart', {})
    
    # Преобразуем service_id в строку для использования в качестве ключа
    service_id_str = str(service_id)
    
    # Получаем количество из формы или устанавливаем 1 по умолчанию
    quantity = int(request.form.get('quantity', 1))
    
    # Если услуга уже в корзине, увеличиваем количество
    if service_id_str in cart:
        cart[service_id_str] += quantity
    else:
        cart[service_id_str] = quantity
    
    session['cart'] = cart
    flash('Услуга добавлена в корзину!')
    return redirect(url_for('catalog.services'))

@bp.route('/cart/remove/<int:service_id>', methods=['POST'])
@login_required
def remove_from_cart(service_id):
    cart = session.get('cart', {})
    service_id_str = str(service_id)
    
    if service_id_str in cart:
        del cart[service_id_str]
        session['cart'] = cart
        flash('Услуга удалена из корзины')
    
    return redirect(url_for('cart.view'))

@bp.route('/cart/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    if request.method == 'POST':
        cart = session.get('cart', {})
        if not cart:
            flash('Корзина пуста!')
            return redirect(url_for('cart.view'))
        
        cur = mysql.connection.cursor()
        
        # Создаем заказ
        try:
            # Вычисляем общую сумму
            total = 0
            for service_id, quantity in cart.items():
                cur.execute("SELECT price FROM services WHERE id = %s", (service_id,))
                price = cur.fetchone()[0]
                total += price * quantity
            
            # Создаем запись в таблице orders
            cur.execute("""
                INSERT INTO orders (user_id, total_amount, status)
                VALUES (%s, %s, 'pending')
            """, (current_user.id, total))
            
            order_id = cur.lastrowid
            
            # Добавляем позиции заказа
            for service_id, quantity in cart.items():
                cur.execute("SELECT price FROM services WHERE id = %s", (service_id,))
                price = cur.fetchone()[0]
                
                cur.execute("""
                    INSERT INTO order_items (order_id, service_id, quantity, price)
                    VALUES (%s, %s, %s, %s)
                """, (order_id, service_id, quantity, price))
            
            mysql.connection.commit()
            
            # Очищаем корзину
            session['cart'] = {}
            
            flash('Заказ успешно оформлен!')
            return redirect(url_for('index'))
            
        except Exception as e:
            mysql.connection.rollback()
            flash('Произошла ошибка при оформлении заказа')
            return redirect(url_for('cart.view'))
        
        finally:
            cur.close()
    
    return render_template('cart/checkout.html')