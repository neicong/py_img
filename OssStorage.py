
import oss2
class OssStorage:
    def __init__(self):
        self.auth = oss2.Auth('LTAI5t9P58naJKGnt7x7zoBp', 'n3k6lb0FZsI1S4mmkW5NJpIFrGfmeG')

    def ossDownload(self,url,file):

        bucket = oss2.Bucket(self.auth, 'http://oss-cn-shanghai.aliyuncs.com', 'tdphotocdn')
        bucket.get_object_to_file(url, file)

