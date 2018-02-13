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
            charset  = self.charset
        )

    def sql(self, statement):
        connect = self.connection
        try:
            with connect.cursor() as cursor:
                cursor.execute(statement)
                result = cursor.fetchall()

                return result
        finally:
            connect.close()