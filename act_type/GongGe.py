import os,zipfile,shutil
from PIL import Image ,ImageFont, ImageDraw,ImageFile,ExifTags
import time
import sys
import traceback
import json
import math
import numpy as np
import requests
from urllib.request import urlopen
from OssStorage import OssStorage
from Logger import Logger
oss = OssStorage()
logger = Logger()
url ="https://picserver.ptdzsw.cn/api/upload"
class GongGe:
    def new_img(self,image_dir_path,resImg,res,db):
        data = {}
        for var in resImg:
            if var['order_goods_id'] in data:
                if var['config_id'] in data[var['order_goods_id']]:
                    data[var['order_goods_id']][var['config_id']].append(var)
                    # data[var['order_goods_id']] = {var['config_id']: [var]}
                else:
                    data[var['order_goods_id']][var['config_id']] = [var]
            else:
                data[var['order_goods_id']] = {var['config_id']:[var]}
        print(data)
        if not os.path.exists(image_dir_path):
            os.mkdir(image_dir_path)


        # img = Image.new('RGB', (int(data['bgw']),int(data['bgh'])),'#FFFFFF')
        for goodskey in data.keys():
            for imgkey in data[goodskey].keys():

                try:
                    configData = json.loads(data[goodskey][imgkey][0]['data'])
                except ValueError as e:
                    configData = False
                    # 创建背景图
                if res['img_url']:
                    img = Image.open(urlopen(res['img_url']))
                    img = img.resize((int(configData['out_frame_width']), int(configData['out_frame_height'])), Image.ANTIALIAS)
                else:
                    img = Image.new('RGB', (int(configData['out_frame_width']), int(configData['out_frame_height'])), '#FFFFFF')
                uid =''
                for val in data[goodskey][imgkey]:
                    uid =uid + '\''+str(val['uid'])+'\','
                    file = self.dowFile(image_dir_path, val)
                    # region = self.resize_by(file, float(configData['img_width'])*float(configData['box_column_height']), float(configData['img_height'])*float(configData['box_column_height']))
                    region = self.resize_by(file, float(configData['box_width']) , float(configData['box_height']))
                    if configData['radius']:
                        region = self.circle_corner(region,int(configData['radius'])*int(configData['box_column_height']))
                    blankLeft = float(configData['blankLeft'])
                    blankTop = float(configData['blankTop'])
                    spacing = float(configData['spacing'])
                    # x = blankLeft + ((float(val['img_sort']) - 1) % float(configData['box_row'])) * (float(configData['img_width'])*float(configData['box_column_height']) + spacing)
                    # y = blankTop + (math.ceil(float(val['img_sort']) / float(configData['box_row'])) - 1) * (
                    #             float(configData['img_height'])*float(configData['box_column_height']) + spacing)
                    x = blankLeft + ((float(val['img_sort']) - 1) % float(configData['box_row'])) * (
                                float(configData['box_width'])  + spacing)
                    y = blankTop + (math.ceil(float(val['img_sort']) / float(configData['box_row'])) - 1) * (
                            float(configData['box_height'])  + spacing)
                    img.paste(region, box=(int(x), int(y)))

                fileName = r'' + image_dir_path + data[goodskey][imgkey][0]['goods_name'] + '-' + data[goodskey][imgkey][0][
                    'content'] + '-'+str(data[goodskey][imgkey][0]['order_goods_id']) +"-"+ 'main_picture' + '.jpg'
                if res['is_primary']:
                    img = img.convert('L')
                    img = img.convert('RGB')

                img.save(fileName.format(time.time()), dpi=[254, 254], quality=95)

                url = self.upload(fileName)
                uid= uid.strip(",")
                updateSql = "update bs_user_img_gat set factory_url = %s where id in ("+uid+")"
                db.cursor.executemany(updateSql, [(url)])
                db.conn.commit()


        # 字体处理
        # if remarks:
        #     if 'textData' in data:
        #         for textData in data['textData']:
        #             if 'tid' in textData:
        #                 if textData['tid'] in remarks:
        #                     img = FontLoading(img, textData, data, remarks[textData['tid']])


        # fileName_1 = r'' + image_dir_path + 'main_picture_1' + '.jpg'
        # img = img.convert('L')
        # img.save(fileName_1.format(time.time()), dpi=[254, 254], quality=95)
            logger.Info(
                {
                    'image_dir_path': image_dir_path,
                    'resImg': resImg,
                    'data': configData,
                }
            )
        # os.unlink(fileName)



        img_zip = str(res['id']) + '.zip'
        self.make_zip(image_dir_path, img_zip)
        url = self.upload(img_zip)
        os.unlink(img_zip)
        self.del_file(image_dir_path)
        return url

    # 下載圖片
    def dowFile(self,fileName, resImg):
        suffix = resImg['img_url'][resImg['img_url'].rfind('.') + 1:]
        suffix = suffix if suffix else 'jpg'
        if not os.path.exists(fileName):
            os.mkdir(fileName)
        file = fileName + resImg['goods_name'] +'-'+ resImg['content'] +'-'+ str(resImg['img_sort']) +"-"+str(resImg['order_goods_id'])+ '.' + suffix
        if not os.path.exists(file):
            img_url = resImg['img_url'].replace('https://cdnpic.iyorclf.cn/', '')
            img_url = img_url.replace('https://cdnpic.ptdzsw.cn/', '')
            oss.ossDownload(img_url, file)
        return file

    def resize_by(self,infile, img_width, img_height):
        """按照宽高进行所需比例缩放"""
        im = Image.open(infile)
        try:
            for orientation in ExifTags.TAGS.keys():
                if ExifTags.TAGS[orientation] == 'Orientation':
                    break
            exif = dict(im._getexif().items())
            if exif[orientation] == 3:
                im = im.rotate(180, expand=True)
            elif exif[orientation] == 6:
                im = im.rotate(270, expand=True)
            elif exif[orientation] == 8:
                im = im.rotate(90, expand=True)
        except:
            pass
        (x, y) = im.size
        # print(x,y)
        if round(x / y, 5) > round(img_width / img_height, 5):  # 按高缩
            hv = round(y / img_height, 5)
            x_s = int(x // hv)
            y_s = int(y // hv)
            wh = int((x_s - img_width) / 2)
            out = im.resize((x_s, y_s), Image.ANTIALIAS)
            out = out.crop(box=(wh, 0, x_s - wh, y_s))
        else:  # 按宽度缩放比例
            hv = round(x / img_width, 5)
            x_s = int(x // hv)
            y_s = int(y // hv)
            wh = int((y_s - img_height) / 2)
            out = im.resize((x_s, y_s), Image.ANTIALIAS)
            out = out.crop(box=(0, wh, x_s, y_s - wh))
        return out

    # 图片上传
    def upload(self,file):
        files = {'file': open(file, 'rb')}
        upload_res = requests.post(url, {"is_login_type":1}, files=files)
        data = upload_res.json()
        if (data['error'] == 0):
            return data['data']['oss_file']

    # 文件打包
    def make_zip(self,source_dir, output_filename):
        zipf = zipfile.ZipFile(output_filename, 'w')
        pre_len = len(os.path.dirname(source_dir))
        for parent, dirnames, filenames in os.walk(source_dir):
            for filename in filenames:
                pathfile = os.path.join(parent, filename)
                arcname = pathfile[pre_len:].strip(os.path.sep)  # 相对路径
                zipf.write(pathfile, arcname)
        zipf.close()

    # 文件删除
    def del_file(self,filepath):
        """
        删除某一目录下的所有文件或文件夹
        :param filepath: 路径
        :return:
        """
        del_list = os.listdir(filepath)
        for f in del_list:
            file_path = os.path.join(filepath, f)
            if os.path.isfile(file_path):
                os.remove(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        shutil.rmtree(filepath)

    # 圆角
    def circle_corner(self,im, rad):
        (x, y) = im.size
        imb = Image.new('RGBA', (x, y), (255, 255, 255, 0))
        imb1 = Image.new('RGBA', (x, y), (255, 255, 255, 0))
        imb2 = Image.new('RGBA', (x, y), (255, 255, 255, 0))
        imb3 = Image.new('RGBA', (x, y), (255, 255, 255, 0))
        region = im.load()
        pimb = imb.load()
        pimb1 = imb1.load()
        pimb2 = imb2.load()
        pimb3 = imb3.load()
        r = float(rad / 2)
        for i in range(x):
            for j in range(y):
                #
                lx = abs(i - r + 0.5)  # 到圆心距离的横坐标
                ly = abs(j - r + 0.5)  # 到圆心距离的纵坐标
                l = pow(lx, 2) + pow(ly, 2)

                #

                if l <= pow(r, 2):
                    pimb[i, j] = region[i, j]
                else:
                    if (float(i) > r) | (float(j) > r):
                        pimb[i, j] = region[i, j]

        for i in range(x):
            for j in range(y):
                lx = abs(i - x + r + 0.5)  # 到圆心距离的横坐标
                ly = abs(j - y + r + 0.5)  # 到圆心距离的纵坐标
                l = pow(lx, 2) + pow(ly, 2)
                if l <= pow(r, 2):
                    pimb1[i, j] = pimb[i, j]
                else:
                    if (float(i) < x - r) | (float(j) < y - r):
                        pimb1[i, j] = pimb[i, j]

        for i in range(x):
            for j in range(y):
                lx = abs(i - r + 0.5)  # 到圆心距离的横坐标
                ly = abs(j - y + r + 0.5)  # 到圆心距离的纵坐标
                l = pow(lx, 2) + pow(ly, 2)
                if l <= pow(r, 2):
                    pimb2[i, j] = pimb1[i, j]
                else:
                    if (float(i) > r) | (float(j) < y - r):
                        pimb2[i, j] = pimb1[i, j]

        for i in range(x):
            for j in range(y):
                lx = abs(i - x + r + 0.5)  # 到圆心距离的横坐标
                ly = abs(j - r + 0.5)  # 到圆心距离的纵坐标
                l = pow(lx, 2) + pow(ly, 2)
                if l <= pow(r, 2):
                    pimb3[i, j] = pimb2[i, j]
                else:
                    if (float(i) < x - r) | (float(j) > r):
                        pimb3[i, j] = pimb2[i, j]
        return imb3
