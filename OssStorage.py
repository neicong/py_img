
import oss2
class OssStorage:
    def __init__(self):
        self.auth = oss2.Auth('LTAI4GGAs1EyNgFnepHpaqQi', '3KfcHzyS6ifVsG5IHPsLZopkw1tJdq')

    def ossDownload(self,url,file):

        bucket = oss2.Bucket(self.auth, 'http://oss-cn-shanghai.aliyuncs.com', 'tdphotocdn')
        bucket.get_object_to_file(url, file)

