import pymysql
from dbutils.pooled_db import PooledDB
class MysqlPool:
    # 本地
    # config = {
    #     'creator': pymysql,
    #     'host': '192.168.137.10',
    #     'port': 3306,
    #     'user': 'root',
    #     'password': 'NieCong@cn:80',
    #     'db': 'notice_board_server',
    #     'charset': 'utf8',
    #     'maxconnections': 10,  # 连接池最大连接数量
    #     'cursorclass': pymysql.cursors.DictCursor
    # }
    # 测试环境
    # config = {
    #     'creator': pymysql,
    #     'host': '127.0.0.1',
    #     'port': 3306,
    #     'user': 'sql_pic_tdcm88',
    #     'password': 'AAtnhr8pPPJcFdTZ',
    #     'db': 'sql_pic_tdcm88',
    #     'charset': 'utf8',
    #     'maxconnections': 10,  # 连接池最大连接数量
    #     'cursorclass': pymysql.cursors.DictCursor
    # }

    # 正式环境
    config = {
        'creator': pymysql,
        'host': 'rm-uf6p32e62h6f51rr333150.mysql.rds.aliyuncs.com',
        'port': 3306,
        'user': 'picserver',
        'password': 'syBnmWdCcrJXX27b',
        'db': 'picserver',
        'charset': 'utf8',
        'maxconnections': 10,  # 连接池最大连接数量
        'cursorclass': pymysql.cursors.DictCursor
    }
    pool = PooledDB(**config)

    def __enter__(self):
        self.conn = MysqlPool.pool.connection()
        self.cursor = self.conn.cursor()
        return self

    def __exit__(self, type, value, trace):
        self.cursor.close()
        self.conn.close()
