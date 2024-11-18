# models/service.py
class Service:
    def __init__(self, id, name, description, price, image_path):
        self.id = id
        self.name = name
        self.description = description
        self.price = price
        self.image_path = image_path

    @staticmethod
    def get_all(mysql):
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM services")
        services = cur.fetchall()
        cur.close()
        return [Service(s[0], s[1], s[2], s[3], s[4]) for s in services]