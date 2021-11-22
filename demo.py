# coding:utf-8
import os,zipfile,shutil
import pymysql
from PIL import Image ,ImageFont, ImageDraw,ImageFile,ExifTags
import time
import sys
import traceback
import json
import math
import requests
from urllib.request import urlopen
from MysqlPool import MysqlPool
from OssStorage import OssStorage
from Logger import Logger
ImageFile.LOAD_TRUNCATED_IMAGES = True
sql = 'select a.id,a.order_id,a.config_id,a.img_url,a.title,a.is_primary,b.data from bs_order_gat a left join bs_template b on a.config_id = b.id where a.status = 0 and a.config_id!=0 order by a.order_update_time asc;'
oss = OssStorage()
# url = "https://testpicserver.ptdzsw.cn/api/upload"
url ="https://picserver.ptdzsw.cn/api/upload"

# AIurl = "https://testpicserver.ptdzsw.cn/api/uploadBaiduAi"
AIurl ="https://picserver.ptdzsw.cn/api/uploadBaiduAi"
oss = OssStorage()
Imageoss = OssStorage()
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
                    ###加锁
                    updateSql = "update bs_order_gat set status=2 where id=%s"
                    db.cursor.executemany(updateSql, [(res['id'])])
                    db.conn.commit()


                    sqlImg = "select * from bs_user_img_gat where gat_id=%s" % res['id']
                    db.cursor.execute(sqlImg)
                    resImg = db.cursor.fetchall()
                    if (resImg):
                        if (res['data']):
                            try:
                                data = json.loads(res['data'])
                            except ValueError as e:
                                data = False
                            # image_dir_path = r'/tmp/' + str(res['order_id']) + '/'
                            image_dir_path = r'img/'
                            # try:
                            #     remarks = json.loads(res['remarks'])
                            # except ValueError as e:
                            #     remarks = False


                            # try:
                            #     is_primary = res['is_primary']
                            #     print("程序运行id：%s s" % res['id'])
                            #     url,zipurl = new_image(res['id'],image_dir_path, resImg, data,res['img_url'],is_primary)
                            #     updateSql = "update bs_order_gat set status=1,main_img = %s,img_zip=%s where id=%s"
                            # except:
                            #     url = ''
                            #     zipurl='1'
                            #     if os.path.exists(image_dir_path):
                            #         del_file(image_dir_path)
                            #     updateSql = "update bs_order_gat set status=2,main_img = %s,img_zip=%s where id=%s"

                            is_primary = res['is_primary']
                            print("程序运行id：%s s" % res['id'])
                            url, zipurl = new_image(res['id'], image_dir_path, resImg, data, res['img_url'],
                                                    is_primary)
                            updateSql = "update bs_order_gat set status=1,main_img = %s,img_zip=%s where id=%s"
                            # try:
                            #     is_primary = res['is_primary']
                            #     print("程序运行id：%s s" % res['id'])
                            #     url, zipurl = new_image(res['id'], image_dir_path, resImg, data, res['img_url'],
                            #                             is_primary)
                            #     updateSql = "update bs_order_gat set status=1,main_img = %s,img_zip=%s where id=%s"
                            # except:
                            #     url = ''
                            #     zipurl = ''
                            #     if os.path.exists(image_dir_path):
                            #         del_file(image_dir_path)
                            #     updateSql = "update bs_order_gat set status=2,main_img = %s,img_zip=%s where id=%s"
                            db.cursor.executemany(updateSql, [(url,zipurl, res['id'])])
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
        img_url =img_url.replace('https://cdnpic.ptdzsw.cn/', '')
        oss.ossDownload(img_url, file)
    return file


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
        hv = round(y / img_height,5) + 0.001
        x_s = int(x // hv)
        y_s = int(y // hv)
        wh = int((x_s - img_width) / 2)
        out = im.resize((x_s, y_s), Image.ANTIALIAS)
        out = out.crop(box=(wh, 0,x_s-wh , y_s))
    else: #按宽度缩放比例
        hv = round(x / img_width,5)+0.001
        x_s = int(x // hv)
        y_s = int(y // hv)
        wh = int((y_s - img_height) / 2)
        out = im.resize((x_s, y_s), Image.ANTIALIAS)
        out = out.crop(box=(0, wh, x_s , y_s-wh))
    return out




def new_image(id,image_dir_path,resImg,data,infile,is_primary):
    starttime = time.time()
    # 创建背景图
    if infile:
        img = Image.open(urlopen(infile))
        img = img.resize((int(data['out_frame_width']), int(data['out_frame_height'])), Image.ANTIALIAS)
    else:
        img = Image.new('RGB', (int(data['out_frame_width']), int(data['out_frame_height'])), '#FFFFFF')

    # img = Image.new('RGB', (int(data['bgw']),int(data['bgh'])),'#FFFFFF')

    for val in resImg:
        file = dowFile(image_dir_path,val)
        region = resize_by(file, float(data['box_width']),float(data['box_height']))
        if data['radius']:
            region = circle_corner(region, int(data['radius']) * int(data['box_column_height']))

        blankLeft = float(data['blankLeft'])
        blankTop =float(data['blankTop'])
        spacing= float(data['spacing'])
        x = blankLeft +((float(val['img_sort'])-1)%float(data['box_row']))*(float(data['box_width'])+spacing)
        y = blankTop + (math.ceil(float(val['img_sort'])/float(data['box_row']))-1) * (float(data['box_height']) + spacing)
        img.paste(region, box=(int(x), int(y)))

    #字体处理
    # if remarks:
    #     if 'textData' in data:
    #         for textData in data['textData']:
    #             if 'tid' in textData:
    #                 if textData['tid'] in remarks:
    #                     img = FontLoading(img, textData, data, remarks[textData['tid']])



    endtime = time.time()
    dtime = endtime - starttime
    print("程序运行时间：%s s" % dtime)  # 显示到微秒
    fileName =r''+image_dir_path+'main_picture'+'.jpg'
    if is_primary:
        img = img.convert('L')
        img = img.convert('RGB')
    img.save(fileName.format(time.time()), dpi=[254, 254],quality=95)

    # fileName_1 = r'' + image_dir_path + 'main_picture_1' + '.jpg'
    # img = img.convert('L')
    # img.save(fileName_1.format(time.time()), dpi=[254, 254], quality=95)
    logger.Info(
        {
            'image_dir_path': image_dir_path,
            'resImg': resImg,
            'data': data,
            'dtime': dtime
        }
    )
    url = upload(fileName)
    # AI圖片刪除
    AIupload(id,fileName)
    img_zip = str(id) + '.zip'
    make_zip(image_dir_path, img_zip)
    zipurl=''
    if(os.path.getsize(img_zip) < 50*1024*1024):
        zipurl = upload(img_zip)

    if os.path.exists(img_zip):
        try:
            os.unlink(img_zip)
        except:
            zipurl=''
    del_file(image_dir_path)
    return url,zipurl



#图片上传
def upload(file):
    files = {'file': open(file, 'rb')}
    upload_res = requests.post(url, {"is_login_type":1}, files=files)
    data = upload_res.json()
    if(data['error']==0):
        return data['data']['oss_file']

#百度AI上传
def AIupload(id,file):
    files = {'file': open(file, 'rb')}
    upload_res = requests.post(AIurl, {"id":id}, files=files)
    print(upload_res)
    data = upload_res.json()
    print(data)
    if(data['error']==0):
        return data['data']



#字体加载
def FontLoading(img,textData,data,word):
    if 'Siyuan' in textData['tfont']:
        SimHei = "https://cdnpic.iyorclf.cn/web/SourceHanSansCN-Normal.ttf"  # 一个字体文件
    else:
        SimHei = "123.ttf"  # 一个字体文件
    font = ImageFont.truetype(urlopen(SimHei), int(textData['tSize']) * 4,encoding="unic")  # 设置字体和大小
    w, h = font.getsize(word)  #
    draw = ImageDraw.Draw(img)
    draw.text((int((float(data['bgw']) - w) / 2), int(textData['tTop'])), word, fill=textData['tColor'], font=font)
    return img

#圆角
def circle_corner(im, rad):
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

 # 文件打包
def make_zip(source_dir, output_filename):
    zipf = zipfile.ZipFile(output_filename, 'w')
    pre_len = len(os.path.dirname(source_dir))
    for parent, dirnames, filenames in os.walk(source_dir):
        for filename in filenames:
            pathfile = os.path.join(parent, filename)
            arcname = pathfile[pre_len:].strip(os.path.sep)  # 相对路径
            zipf.write(pathfile, arcname)
    zipf.close()

if __name__ == '__main__':
    set_gpus(10)
    res = timer()
    print(res)

