# coding:utf-8
import os,zipfile,shutil
import pymysql
from PIL import Image ,ImageFont, ImageDraw,ImageFile,ExifTags
import time
import traceback
import json
import math
import requests
from urllib.request import urlopen
from MysqlPool import MysqlPool
from OssStorage import OssStorage
from Logger import Logger

from act_type.GongGe import GongGe
import re
ImageFile.LOAD_TRUNCATED_IMAGES = True
logger = Logger()

# sql = 'SELECT o.id,o.order_id,o.bs_moblie,o.is_primary,o.bs_name,g.goods_name,t.data,t.content,u.img_url,u.id as uid FROM bs_user_img_gat u LEFT JOIN bs_template t ON u.config_id = t.id LEFT JOIN bs_order_goods g ON u.order_goods_id = g.id LEFT JOIN bs_order o ON u.order_id = o.order_id WHERE o.status = 0 AND o.del = 0 AND u.version=2 AND g.del=0 ORDER BY o.id DESC;'
# sql ="SELECT o.id,o.order_id,o.bs_moblie,o.is_primary,o.bs_name,g.goods_name,t.data,t.content,u.img_url,n.taobao_id,n.red_name,n.order_ate,u.id AS uid FROM bs_user_img_gat u LEFT JOIN bs_template t ON u.config_id = t.id LEFT JOIN bs_order_goods g ON u.order_goods_id = g.id LEFT JOIN bs_order o ON u.order_id = o.order_id LEFT JOIN bs_order_review w ON w.ve_order_id = o.id	LEFT JOIN order_syn n ON n.id = w.syn_id WHERE o.status = 0 AND o.del = 0 AND u.version = 2 AND g.del = 0 ORDER BY o.id DESC;"
# sql ="SELECT o.id,o.order_id,o.is_primary,t.`data`,t.ate_id,t.content,u.img_url,u.id AS uid FROM bs_user_img_gat u LEFT JOIN bs_template t ON u.config_id = t.id LEFT JOIN bs_order o ON u.order_id = o.order_id WHERE o.`status` = 0  AND o.del = 0 AND u.version = 2 ORDER BY o.id DESC;"
sql ="select id,order_id,is_primary,img_url from bs_order WHERE `status` = 0 AND del=0 order by id desc;"
numbers ={
    0: GongGe,
    1: GongGe,
    2: GongGe,
    3: GongGe,
    4: GongGe,
    5:'',
    6: GongGe,
}
oss = OssStorage()
# url = "https://testpicserver.iyorclf.cn/api/upload"
url ="https://picserver.ptdzsw.cn/api/upload"

def timer():

    while True:
        try:
            with MysqlPool() as db:
                db.cursor.execute(sql)
                res = db.cursor.fetchone()
                if (res):
                    starttime = time.time()
                    data = {}
                    sqlImg = "SELECT t.`data`,t.draw_data,t.ate_id,t.content,u.img_url,u.id AS uid,u.order_goods_id,u.img_sort,u.config_id,g.goods_name FROM bs_user_img_gat u LEFT JOIN bs_template t ON u.config_id = t.id LEFT JOIN bs_order_goods g ON g.id = u.order_goods_id WHERE u.order_id='%s' and u.version = 2 ORDER BY u.img_sort ASC;" % res['order_id']
                    db.cursor.execute(sqlImg)
                    resImg = db.cursor.fetchall()
                    # for var in res:
                    #     if var['id'] in data:
                    #        data[var['id']].append(var)
                    #     else:
                    #         data[var['id']] = [var]


                    method = numbers.get(resImg[0]['ate_id'])
                    image_dir_path = r'/tmp/' + str(res['id']) + '/'
                    # image_dir_path = r'img/'
                    if method:
                        url = method().new_img(image_dir_path,resImg,res,db)
                    else:
                        url = new_image(image_dir_path, resImg, res,db)

                    updateSql = "update bs_order set status=1,img_zip = %s where id=%s"
                    db.cursor.executemany(updateSql, [(url, res['id'])])
                    db.conn.commit()

                    # for key in data:
                    #     image_dir_path = r'/tmp/' + str(key) + '/'
                    #     # image_dir_path = r'img/'
                    #     url = new_image(image_dir_path,data[key],key,db)
                    #     updateSql = "update bs_order set status=1,img_zip = %s where id=%s"
                    #     db.cursor.executemany(updateSql, [(url, key)])
                    #     db.conn.commit()

                    endtime = time.time()
                    dtime = endtime - starttime
                    print("程序运行时间：%s s" % dtime)  # 显示到微秒

        except ZeroDivisionError as e1:
            logger.Warning(traceback.format_exc())
        finally:
            time.sleep(10)
        time.sleep(5)





def resize_by(infile, img_width,img_height):
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
    if round(x/y,5)>round(img_width/img_height,5): #按高缩
        hv = round(y / img_height,10)
        x_s = int(x // hv)
        y_s = int(y // hv)
        wh = int((x_s - img_width) / 2)
        out = im.resize((x_s, y_s), Image.ANTIALIAS)
        out = out.crop(box=(wh, 0,x_s-wh , y_s))
    else: #按宽度缩放比例
        hv = round(x / img_width,10)
        x_s = int(x // hv)
        y_s = int(y // hv)
        wh = int((y_s - img_height) / 2)
        out = im.resize((x_s, y_s), Image.ANTIALIAS)
        out = out.crop(box=(0, wh, x_s , y_s-wh))
    return out

def new_image(image_dir_path,data,res,db):
    if not os.path.exists(image_dir_path):
        os.mkdir(image_dir_path)
    sort =1
    for val in data:
        try:
            configData = json.loads(val['data'])
        except ValueError as e:
            configData = False
        if(configData):
            img_url = dowFile(image_dir_path,val['img_url'],res['order_id'],sort)
            img =  resize_by(img_url,int(configData['out_frame_width']), int(configData['out_frame_height']))
            # img = Image.open(urlopen(val['img_url']))
            # img = img.resize((int(configData['out_frame_width']), int(configData['out_frame_height'])), Image.ANTIALIAS)
            # suffix = val['img_url'][val['img_url'].rfind('.') + 1:]
            # suffix = suffix if suffix else 'jpg'
            suffix = 'jpg'
            fileName = str(res['order_id'])+'(出厂图)-' + \
                       str(sort)
            fileName = strip_control_characters(fileName)
            fileName =  r'' + image_dir_path+fileName+'.'+ suffix
            print(fileName)
            if res['is_primary']:
                img = img.convert('L')
                img = img.convert('RGB')
            img = img.convert('RGB')
            img.save(fileName.format(time.time()), dpi=[254, 254], quality=95)
            sort +=1

            imgUrl = upload(fileName)
            updateSql = "update bs_user_img_gat set factory_url = %s where id=%s"
            db.cursor.executemany(updateSql, [(imgUrl, val['uid'])])
            db.conn.commit()


    img_zip =str(res['id'])+'.zip'
    make_zip(image_dir_path,img_zip)
    url = upload(img_zip)
    os.unlink(img_zip)
    del_file(image_dir_path)
    return url


#下載圖片
def dowFile(fileName,resImg,order_id,sort):
    suffix = resImg[resImg.rfind('.') + 1:]
    suffix = suffix if suffix else 'jpg'
    if not os.path.exists(fileName):
        os.mkdir(fileName)
    file = fileName + str(order_id) + '(原图)-'+str(sort)+'.' + suffix
    if not os.path.exists(file):
        img_url = resImg.replace('https://cdnpic.iyorclf.cn/', '')
        img_url =img_url.replace('https://cdnpic.ptdzsw.cn/', '')
        oss.ossDownload(img_url, file)
    return file

#图片上传
def upload(file):
    files = {'file': open(file, 'rb')}
    upload_res = requests.post(url, {"is_login_type":1}, files=files)
    data = upload_res.json()
    if(data['error']==0):
        return data['data']['oss_file']
#文件打包
def make_zip(source_dir, output_filename):
  zipf = zipfile.ZipFile(output_filename, 'w')
  pre_len = len(os.path.dirname(source_dir))
  for parent, dirnames, filenames in os.walk(source_dir):
    for filename in filenames:
      pathfile = os.path.join(parent, filename)
      arcname = pathfile[pre_len:].strip(os.path.sep)   #相对路径
      zipf.write(pathfile, arcname)
  zipf.close()
#文件删除
def del_file(filepath):
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

#去掉特殊符号
def strip_control_characters(s):
    rstr = r"[\/\\\:\*\?\"\<\>\|]"  # '/ \ : * ? " < > |'
    new_title = re.sub(rstr, "_", s)  # 替换为下划线
    return new_title


if __name__ == '__main__':

    res = timer()
    print(res)