import pymysql

class DataBase(object):
    def __init__(self, name,
        host     = 'localhost',
        port     = 3306,
        user     = '',
        password = '',
        charset  = 'utf8',
        connect  = True
    ):
        self.name     = name
        self.host     = host
        self.port     = port
        self.user     = user
        self.password = password
        self.charset  = charset

        if connect:
            self.connect()

    def connect(self):
        self.connection = pymysql.connect(
            host     = self.host,
            port     = self.port,
            user     = self.user,
            password = self.password,
            db       = self.name,
            charset  = self.charset,
            cursorclass = pymysql.cursors.DictCursor
        )

    def sql(self, statement):
        if not self.connection.open:
            self.connect()
            
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(statement)
                result = cursor.fetchall()

                return result
        finally:
            self.connection.close()