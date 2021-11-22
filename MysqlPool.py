import pymysql
from dbutils.pooled_db import PooledDB
class MysqlPool:
    # 本地
    config = {
        'creator': pymysql,
        'host': '192.168.137.10',
        'port': 3306,
        'user': 'root',
        'password': 'NieCong@cn:80',
        'db': 'notice_board_server',
        'charset': 'utf8',
        'maxconnections': 10,  # 连接池最大连接数量
        'cursorclass': pymysql.cursors.DictCursor
    }
    # 测试环境


    # 正式环境

    pool = PooledDB(**config)

    def __enter__(self):
        self.conn = MysqlPool.pool.connection()
        self.cursor = self.conn.cursor()
        return self

    def __exit__(self, type, value, trace):
        self.cursor.close()
        self.conn.close()
