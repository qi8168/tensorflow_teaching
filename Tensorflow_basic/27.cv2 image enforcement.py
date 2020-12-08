# -- encoding:utf-8 --
import cv2
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl

# 设置字符集，防止中文乱码
mpl.rcParams['font.sans-serif'] = [u'simHei']
mpl.rcParams['axes.unicode_minus'] = False


def img_color_change():
    img_origin = './images/11.jpg'

    img = cv2.imread(img_origin)  # cv2默认读入进来的格式 是 BGR
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    #HSV(Hue色调， Saturation 饱和度 V亮度)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    #HLS颜色空间，三个分量分别是色相（H）、亮度（L）、饱和度（S）
    hls = cv2.cvtColor(img, cv2.COLOR_BGR2HLS)

    # 定义一个画板
    fig = plt.figure(figsize=(8, 6))  # 代表宽 和高 （单位：英寸）

    # 121的意思是： 整个画板分为 1行2列， a位于第一个位置。
    a = fig.add_subplot(231)
    a.imshow(img)
    a.set_title('original, BGR')

    b = fig.add_subplot(232)
    b.imshow(rgb)
    b.set_title('rgb')

    c = fig.add_subplot(233)
    c.imshow(hsv)
    c.set_title('hsv')

    d = fig.add_subplot(234)
    d.imshow(gray, cmap='Greys')
    d.set_title('gray')

    e = fig.add_subplot(235)
    e.imshow(hls)
    e.set_title('hls')

    plt.show()


def brightness_images(image):
    """
    随机调节图片亮度
    :param image:
    :return:
    """
    # 颜色通道转换   BGR ----> HSV(Hue 色调， Saturation 饱和度  V  亮度)
    #v 就是亮度,我们可以通过改 v 来修改亮度
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    #图片默认是 int8,这里转成 float64
    image1 = np.array(hsv, dtype=np.float64)
    random_bright = 0.5 + np.random.uniform()  # 随机调亮 或者调暗的随机数生成 0:1.5
    print(random_bright)
    #对亮度进行随机修改
    image1[:, :, 2] = image[:, :, 2] * random_bright

    # 对于大于255的 进行裁剪。
    image1[:, :, 2][image1[:, :, 2] > 255] = 255
    #数据类型必须改回来
    image1 = np.array(image1, dtype=np.uint8)
    rgb = cv2.cvtColor(image1, cv2.COLOR_HSV2RGB)
    return rgb

def random_bright_img():
    """
    执行随机调整图片亮度
    :return:
    """
    img_origin = './images/11.jpg'
    img = cv2.imread(img_origin)

    #在亮度上随机调整的图片
    brighted_img = brightness_images(img)

    # 定义一个画板
    fig = plt.figure(figsize=(8, 6))  # 代表宽 和高 （单位：英寸）

    # 121的意思是： 整个画板分为 1行2列， a位于第一个位置。
    a = fig.add_subplot(121)
    a.imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    a.set_title("original picture")

    b = fig.add_subplot(122)
    b.imshow(brighted_img)
    b.set_title('adjust brightness')
    plt.show()


def trans_image(image, hori_range, vertical_range):
    """
    实现平移 （线性变换）
    :param image:
    :param hori_range:
    :param vertical_range:
    :return:
    """
    #只在水平和垂直两个维度上移动
    rows, cols, channels = image.shape
    # 定义平移量 tr_x 代表水平平移的量， tr_y 代表垂直平移的量
    tr_x = hori_range*np.random.uniform() - hori_range/2
    tr_y = vertical_range*np.random.uniform() - vertical_range/2

    # 构造仿射关系矩阵。
    trans_matrix = np.float32([[1, 0, tr_x], [0, 1, tr_y]])
    img_trans = cv2.warpAffine(image, trans_matrix, (cols, rows))
    image1 = np.array(img_trans, dtype=np.uint8)
    return image1

def vertical_hrizontal_shift():
    """
    随机水平或者垂直移动图片
    :return:
    """
    img_origin = './images/11.jpg'
    img = cv2.imread(img_origin)
    shifted_img = trans_image(img, hori_range=500, vertical_range=600)

    fig = plt.figure(figsize=(8, 6))  # 代表宽 和高 （单位：英寸）
    a = fig.add_subplot(121)
    a.imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    a.set_title('original pic')

    b = fig.add_subplot(122)
    b.imshow(cv2.cvtColor(shifted_img, cv2.COLOR_BGR2RGB))
    b.set_title('vertical or hrizontal moved')
    plt.show()


def crop_img_and_resize(image):
    shape = image.shape
    print(shape)
    #从图片的宽和高纬度上截取一部分,这里 100 可以设置为一个合适的随机数
    image1 = image[100:shape[0], 100:shape[1]]

    # 需要重新resize 缩放
    new_col = 224
    new_row = 224
    #interpolation=cv2.INTER_AREA是一个图片放大的算法
    image1 = cv2.resize(image1, (new_col, new_row), interpolation=cv2.INTER_AREA)
    return image1


def scale_img():
    img_origin = './images/11.jpg'
    img = cv2.imread(img_origin)
    resized_img = crop_img_and_resize(img)

    fig = plt.figure(figsize=(8, 6))  # 代表宽 和高 （单位：英寸）
    a = fig.add_subplot(121)
    a.imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    a.set_title('original')

    b = fig.add_subplot(122)
    b.imshow(cv2.cvtColor(resized_img, cv2.COLOR_BGR2RGB))
    b.set_title('resized')
    plt.show()

def flip_img(image, flip_mode):
    """
    随机翻转
    :param image:
    :param flip_mode:
    :return:
    """
    randomint_flip = np.random.randint(2)
    if randomint_flip==0:
        # flip_mode 0代表沿着x轴 翻转，  正数代表沿着y轴翻转， 负数沿着2根都翻转。
        image = cv2.flip(image, flip_mode)
    return image


def random_flip_img():
    """
    执行随机翻转
    :return:
    """
    img_origin = './images/11.jpg'
    img = cv2.imread(img_origin)
    flipped_img = flip_img(img, flip_mode=-1)

    fig = plt.figure(figsize=(8, 6))  # 代表宽 和高 （单位：英寸）
    a = fig.add_subplot(121)
    a.imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    a.set_title('original')

    b = fig.add_subplot(122)
    b.imshow(cv2.cvtColor(flipped_img, cv2.COLOR_BGR2RGB))
    b.set_title('flipped')
    plt.show()

def rotation_img(image_src):
    """
    随机旋转
    :param image_src:
    :return:
    """
    #旋转只能在前两个维度上进行
    rows, cols = image_src.shape[:2]
    # 定义一个随机旋转的随机数
    rotation_randomint = np.random.randint(low=180)
    print(rotation_randomint)
    # 定义一个旋转映射的矩阵。scale:缩放比例,(cols/2, rows/2)是旋转中心,这里选择图片的中心
    rotate_M = cv2.getRotationMatrix2D((cols/2, rows/2), rotation_randomint, scale = 1.0)
    #borderValue是对边缘填充的颜色,不写的花,默认边缘填充黑色
    rotated_img = cv2.warpAffine(image_src, rotate_M, (cols, rows), borderValue=[255, 255, 255])
    return rotated_img


def random_rotated_img():
    img_origin = './images/11.jpg'
    img = cv2.imread(img_origin)
    rotated_img = rotation_img(img)

    fig = plt.figure(figsize=(8, 6))  # 代表宽 和高 （单位：英寸）
    a = fig.add_subplot(121)
    a.imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    a.set_title('original')

    b = fig.add_subplot(122)
    b.imshow(cv2.cvtColor(rotated_img, cv2.COLOR_BGR2RGB))
    b.set_title('rotated')
    plt.show()
















if __name__ == '__main__':
    # img_color_change()
    #scale_img()
    for _ in range(3):
        # random_bright_img()
        #vertical_hrizontal_shift()
        #random_flip_img()
        random_rotated_img()
