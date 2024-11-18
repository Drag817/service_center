# models/order.py
class Order:
    def __init__(self, id, user_id, total_amount, status):
        self.id = id
        self.user_id = user_id
        self.total_amount = total_amount
        self.status = status

    @staticmethod
    def create(mysql, user_id, total_amount):
        cur = mysql.connection.cursor()
        cur.execute(
            "INSERT INTO orders (user_id, total_amount) VALUES (%s, %s)",
            (user_id, total_amount)
        )
        mysql.connection.commit()
        order_id = cur.lastrowid
        cur.close()
        return order_id