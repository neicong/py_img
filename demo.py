# coding:utf-8
import os
import pymysql
from PIL import Image ,ImageFont, ImageDraw
import time
import sys
import traceback
import json
import math
import requests
from MysqlPool import MysqlPool
from OssStorage import OssStorage
from Logger import Logger
sql = 'select a.id,a.order_id,a.config_id,b.draw_data from bs_order_gat a left join bs_template b on a.config_id = b.id where a.status = 0  order by a.id desc;'
oss = OssStorage()
url = "https://testpicserver.iyorclf.cn/api/upload"

oss = OssStorage()
logger = Logger()

def set_gpus(gpu_index):
    if type(gpu_index) == list:
        gpu_index = ','.join(str(_) for _ in gpu_index)
    if type(gpu_index) ==int:
        gpu_index = str(gpu_index)
    os.environ["CUDA_VISIBLE_DEVICES"] = gpu_index
def timer():

    while True:
        try:
            with MysqlPool() as db:
                db.cursor.execute(sql)
                res = db.cursor.fetchone()
                if (res):
                    sqlImg = "select * from bs_user_img_gat where gat_id=%s" % res['id']
                    db.cursor.execute(sqlImg)
                    resImg = db.cursor.fetchall()
                    if (resImg):
                        data = json.loads(res['draw_data'])
                        if (data):
                            image_dir_path = r'/tmp/' + str(res['order_id']) + '/'
                            # image_dir_path = r'img/'
                            url = new_image(image_dir_path, resImg, data)
                            updateSql = "update bs_order_gat set status=1,main_img = %s where id=%s"
                            db.cursor.executemany(updateSql, [(url, res['id'])])
                            db.conn.commit()
        except ZeroDivisionError as e1:
            logger.Warning(traceback.format_exc())
        finally:
            time.sleep(10)
        time.sleep(5)

#下載圖片
def dowFile(fileName,resImg):
    suffix = resImg['img_url'][resImg['img_url'].rfind('.') + 1:]
    suffix = suffix if suffix else 'jpg'
    if not os.path.exists(fileName):
        os.mkdir(fileName)
    file = fileName + str(resImg['img_sort']) + '.' + suffix
    if not os.path.exists(file):
        img_url = resImg['img_url'].replace('https://cdnpic.iyorclf.cn/', '')
        oss.ossDownload(img_url, file)
    return file


def resize_by(infile, img_width,img_height):
    """按照宽高进行所需比例缩放"""
    im = Image.open(infile)
    (x, y) = im.size
    # print(x,y)
    if round(x/y,5)>round(img_width/img_height,5): #按高缩
        hv = round(y / img_height,2) + 0.001
        x_s = int(x // hv)
        y_s = int(y // hv)
        wh = int((x_s - img_width) / 2)
        out = im.resize((x_s, y_s), Image.ANTIALIAS)
        out = out.crop(box=(wh, 0,x_s-wh , y_s))
    else: #按宽度缩放比例
        hv = round(x / img_width,2)+0.001
        x_s = int(x // hv)
        y_s = int(y // hv)
        wh = int((y_s - img_height) / 2)
        out = im.resize((x_s, y_s), Image.ANTIALIAS)
        out = out.crop(box=(0, wh, x_s , y_s-wh))
    return out




def new_image(image_dir_path,resImg,data):
    starttime = time.time()
    # 创建背景图
    img = Image.new('RGB', (int(data['bgw']),int(data['bgh'])),'#FFFFFF')

    for val in resImg:
        file = dowFile(image_dir_path,val)
        region = resize_by(file, float(data['imgW']),float(data['imgH']))
        blankLeft = float(data['blankLeft'])
        blankTop =float(data['blankTop'])
        spacing= float(data['spacing'])
        x = blankLeft +((float(val['img_sort'])-1)%float(data['row']))*(float(data['imgW'])+spacing)
        y = blankTop + (math.ceil(float(val['img_sort'])/float(data['row']))-1) * (float(data['imgH']) + spacing)
        img.paste(region, box=(int(x), int(y)))
    endtime = time.time()
    dtime = endtime - starttime
    print("程序运行时间：%s s" % dtime)  # 显示到微秒
    fileName =r'py_img_'+format(time.time())+'.jpg'
    img.save(fileName.format(time.time()), dpi=[254, 254],quality=95)
    logger.Info(
        {
            'image_dir_path': image_dir_path,
            'resImg': resImg,
            'data': data,
            'dtime': dtime
        }
    )
    url = upload(fileName)
    os.unlink(fileName)
    return url



#图片上传
def upload(file):
    files = {'file': open(file, 'rb')}
    upload_res = requests.post(url, {}, files=files)
    data = upload_res.json()
    if(data['error']==0):
        return data['data']['oss_file']




if __name__ == '__main__':

    set_gpus(10)
    res = timer()
    # print(res)

