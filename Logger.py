import logging
import datetime
import json
import time
import os
#json重写
class DateEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj,datetime.datetime):
            return obj.strftime("%Y-%m-%d %H:%M:%S")
        else:
            return json.JSONEncoder.default(self,obj)

class Logger:

    def __init__(self):
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.INFO)
        file = './log/'
        if not os.path.exists(file):
            os.mkdir(file)
        fh = logging.FileHandler( file + time.strftime('%Y-%m-%d') + '.log', mode='a')
        formatter = logging.Formatter("%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s")
        fh.setFormatter(formatter)
        self.logger.addHandler(fh)


    def Error(self,data):
        data = json.dumps(data , cls=DateEncoder)
        self.logger.error(data)

    def Info(self,data):
        data = json.dumps(data , cls=DateEncoder)
        self.logger.info(data)

    def Debug(self, data):
        data = json.dumps(data, cls=DateEncoder)
        self.logger.debug(data)

    def Warning(self, data):
        data = json.dumps(data, cls=DateEncoder)
        self.logger.warning(data)