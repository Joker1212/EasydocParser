import os
from io import BytesIO

import cv2
import numpy
import requests
from PIL import ImageDraw, Image, ImageOps

def download_image(image_url):
    try:
        response = requests.get(image_url, timeout=5)
        if response.status_code == 200:
            return response.content
    except requests.RequestException:
        pass
    return None

def get_image_size(image_data):
    try:
        image = Image.open(BytesIO(image_data))
        width, height = image.size
        return image, width, height
    except Exception as e:
        print(f"Error processing image: {e}")
        return None, None, None

def get_croped_image(image_pil, bbox, expand = None, fill_color = (255,255,255)):
    x_min, y_min, x_max, y_max = bbox
    croped_img = image_pil.crop((x_min, y_min, x_max, y_max))
    if expand is not None:
        return ImageOps.expand(croped_img, border=expand, fill=fill_color)
    return croped_img


def add_layout_box_to_img(layout_boxes, ori_img_save_path):
    img = cv2.imread(ori_img_save_path)
    # 检查图像是否成功读取
    if img is None:
        raise IOError("Failed to load image file:")

    for idx, box in enumerate(layout_boxes):
        x0, y0, x1, y1 = box.bbox
        x0 = round(x0)
        y0 = round(y0)
        x1 = round(x1)
        y1 = round(y1)
        cv2.rectangle(img, (x0, y0), (x1, y1), (0, 0, 255), 1)

        # 增大字体大小和线宽
        font_scale = 1.0  # 原先是0.5
        thickness = 2  # 原先是1

        cv2.putText(
            img,
            str(idx) + '.' + box.label,
            (x1, y1),
            cv2.FONT_HERSHEY_PLAIN,
            font_scale,
            (0, 0, 255),
            thickness,
        )
    return img


def cross_section_paste_to_first(tuple_list, margin=15, background_color=(255, 255, 255)):
    cur_img, cur_valid_box, cur_stable_boxes, cur_offset_boxes, cur_box = tuple_list[0]
    next_img, next_valid_box, next_stable_boxes, next_offset_boxes, next_box = tuple_list[1]
    next_box_width = next_box[2] - next_box[0]
    next_box_height = next_box[3] - next_box[1]
    top_offset = cur_valid_box[1]
    height_extend = next_box_height + margin
    height_bottom_margin = cur_img.height - cur_valid_box[3]
    new_height = cur_valid_box[3] - cur_valid_box[1] + top_offset + height_extend + height_bottom_margin
    # 留出 8 * margin像素点空白，避免识别框的边缘不清楚
    extended_image = Image.new('RGB',
                               (cur_img.width, int(new_height)),
                               color=background_color)
    for box in cur_stable_boxes:
        cropped_image = cur_img.crop(box)
        extended_image.paste(cropped_image, (int(box[0]), int(box[1])))
    for box in cur_offset_boxes:
        cropped_image = cur_img.crop(box)
        extended_image.paste(cropped_image, (int(box[0]), int(box[1] + height_extend)))
    footer_crop = cur_img.crop((0, cur_valid_box[3], cur_img.width, cur_img.height))
    cropped_image = next_img.crop(next_box)
    crop_xmin = int(cur_box[0])
    crop_ymin = int(cur_box[3]) + margin
    extended_image.paste(cropped_image, (crop_xmin, crop_ymin))
    extended_image.paste(footer_crop, (0, int(cur_valid_box[3] + height_extend)))
    return extended_image, height_extend, numpy.array((crop_xmin, crop_ymin, crop_xmin + next_box_width, crop_ymin + next_box_height))


def cross_section_paste_to_next(tuple_list, margin=15, background_color=(255, 255, 255)):
    cur_img, cur_valid_box, cur_stable_boxes, cur_offset_boxes, cur_box = tuple_list[0]
    next_img, next_valid_box, next_stable_boxes, next_offset_boxes, next_box = tuple_list[1]
    cur_box_width = cur_box[2] - cur_box[0]
    cur_box_height = cur_box[3] - cur_box[1]
    top_offset = next_valid_box[1]
    height_extend = cur_box[3] - cur_box[1] + margin
    height_bottom_margin = next_img.height - next_valid_box[3]
    new_height = next_valid_box[3] - next_valid_box[1] + top_offset + height_extend + height_bottom_margin
    # 留出 8 * margin像素点空白，避免识别框的边缘不清楚
    extended_image = Image.new('RGB',
                               (next_img.width, int(new_height)),
                               color=background_color)
    for box in next_stable_boxes:
        cropped_image = next_img.crop(box)
        extended_image.paste(cropped_image, (int(box[0]), int(box[1])))
    for box in next_offset_boxes:
        cropped_image = next_img.crop(box)
        extended_image.paste(cropped_image, (int(box[0]), int(box[1] + height_extend)))
    footer_crop = cur_img.crop((0, cur_valid_box[3], cur_img.width, cur_img.height))
    cropped_image = cur_img.crop(cur_box)
    crop_xmin = int(next_box[0])
    crop_ymin = int(next_box[1])
    extended_image.paste(cropped_image, (crop_xmin, crop_ymin))
    extended_image.paste(footer_crop, (0, int(next_valid_box[3] + height_extend)))
    return extended_image, height_extend, numpy.array((crop_xmin, crop_ymin, crop_xmin + cur_box_width, crop_ymin + cur_box_height))


def fill_region_with_background_color(image, box_for_crop_list, background_color=(255, 255, 255)):
    """
    将给定图像的指定区域内填充为背景色。

    :param image: PIL.Image 对象
    :param bboxes: 一个列表，每个元素是元组 (xmin, ymin, xmax, ymax)，表示image2中截取的部分
    :param background_color: RGB tuple，表示填充的颜色
    :return: 填充后的 PIL.Image 对象
    """
    # 创建一个ImageDraw对象
    draw = ImageDraw.Draw(image)
    for box in box_for_crop_list:
        rect_coords = (box[:2], box[2:])
        # 使用draw.rectangle()方法填充指定区域
        draw.rectangle(((box[0], box[1]), (box[2], box[3])), fill=background_color)

    return image

if __name__ == '__main__':
    file = f'../output/pdf/行业研究报告/page0.jpg'
    img = cv2.imread(file)
