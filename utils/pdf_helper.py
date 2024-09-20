import json
from io import BufferedReader, BytesIO
from tempfile import SpooledTemporaryFile
from typing import Union, Iterable, List, Tuple, Set, Dict

import fitz
import numpy
from PIL import Image
import numpy as np

abandon_labels = {'header', 'footer', 'reference'}
continuealbe_labels = {'text', 'table'}
textfile_labels = {'title', 'text', 'equation'}
caption_labels = {'table_caption', 'figure_caption'}


# contain_labels = ['text', 'table', 'table_caption', 'reference']
class LayoutBoxEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            # 将 ndarray 转换为列表
            return obj.tolist()
        if isinstance(obj, LayoutBox):
            return obj.to_dict()
        return super().default(obj)


class LayoutBox:
    def __init__(self, bbox, label, score=1.0, box_type='single', merged_bbox=None, text_ocr_res=None, table_html=None):
        """
        初始化LayoutBox类

        :param bbox: 四元组 (xmin, ymin, xmax, ymax)，表示边界框的位置
        :param label: str 类型，表示布局元素的标签
        :param score: float 类型，标识置信度
        :param box_type: str 类型，标识是普通单个布局元素还是多个布局元素合成的, single, merge
        :param merged_bbox: 列表 类型，每个元素是四元组 (xmin, ymin, xmax, ymax)，表示边界框的位置
        """
        self.bbox = bbox
        self.label = label
        self.text_ocr_res = text_ocr_res
        self.layout_direction = 'middle'
        self.table_html = table_html
        self.score = score
        self.box_type = box_type
        self.merged_bbox = merged_bbox

    def to_dict(self):
        """
        将 LayoutBox 对象转换为字典
        """
        return {
            'bbox': self.bbox,
            'label': self.label,
            'text_ocr_res': self.text_ocr_res,
            'score': self.score,
            'box_type': self.box_type,
            'merged_bbox': self.merged_bbox
        }
    # def __str__(self):
    #     return json.dumps(dict(self), ensure_ascii=False)
    #
    # def __repr__(self):
    #     return self.__str__()


def is_contained(box1, box2, threshold=0.2):
    """
    计算是否存在包含关系，返回被包含的box
    """
    b1_x1, b1_y1, b1_x2, b1_y2 = box1[0], box1[1], box1[2], box1[3]
    b2_x1, b2_y1, b2_x2, b2_y2 = box2[0], box2[1], box2[2], box2[3]
    # 不相交直接退出检测
    if b1_x2 < b2_x1 or b1_x1 > b2_x2 or b1_y2 < b2_y1 or b1_y1 > b2_y2:
        return None
    # 计算box2的总面积
    b2_area = (b2_x2 - b2_x1) * (b2_y2 - b2_y1)
    b1_area = (b1_x2 - b1_x1) * (b1_y2 - b1_y1)

    # 计算box1和box2的交集
    intersect_x1 = max(b1_x1, b2_x1)
    intersect_y1 = max(b1_y1, b2_y1)
    intersect_x2 = min(b1_x2, b2_x2)
    intersect_y2 = min(b1_y2, b2_y2)

    # 计算交集的面积
    intersect_area = max(0, intersect_x2 - intersect_x1) * max(0, intersect_y2 - intersect_y1)

    # 计算外面的面积
    b1_outside_area = b1_area - intersect_area
    b2_outside_area = b2_area - intersect_area

    # 计算外面的面积占box2总面积的比例
    ratio_b1 = b1_outside_area / b1_area if b1_area > 0 else 0
    ratio_b2 = b2_outside_area / b2_area if b2_area > 0 else 0

    if ratio_b1 < threshold:
        return 1
    if ratio_b2 < threshold:
        return 2
    # 判断比例是否大于阈值
    return None


def is_single_axis_contained(box1, box2, axis='x', threshold=0.2):
    """
    判断两个box是否在某一个轴上重叠，返回重叠的轴
    :param box1:
    :param box2:
    :param threshold:
    :return:
    """
    b1_x1, b1_y1, b1_x2, b1_y2 = box1[0], box1[1], box1[2], box1[3]
    b2_x1, b2_y1, b2_x2, b2_y2 = box2[0], box2[1], box2[2], box2[3]

    # 计算轴重叠大小
    if axis == 'x':
        b1_area = (b1_x2 - b1_x1)
        b2_area = (b2_x2 - b2_x1)
        i_area = min(b1_x2, b2_x2) - max(b1_x1, b2_x1)
    else:
        b1_area = (b1_y2 - b1_y1)
        b2_area = (b2_y2 - b2_y1)
        i_area = min(b1_y2, b2_y2) - max(b1_y1, b2_y1)
        # 计算外面的面积
    b1_outside_area = b1_area - i_area
    b2_outside_area = b2_area - i_area

    ratio_b1 = b1_outside_area / b1_area if b1_area > 0 else 0
    ratio_b2 = b2_outside_area / b2_area if b2_area > 0 else 0
    if ratio_b1 < threshold:
        return 1
    if ratio_b2 < threshold:
        return 2
    return None


def distance(box_1, box_2):
    """
    两个坐标轴距离 + 最小的一个坐标轴方向距离
    :param box_1:
    :param box_2:
    :return:
    """
    b1_x1, b1_y1, b1_x2, b1_y2 = box_1
    b2_x1, b2_y1, b2_x2, b2_y2 = box_2
    dis = abs(b2_x1 - b1_x1) + abs(b2_y1 - b1_y1) + abs(b2_x2 - b1_x2) + abs(b2_y2 - b1_y2)
    dis_x = abs(b2_x1 - b1_x1) + abs(b2_y1 - b1_y1)
    dis_y = abs(b2_x2 - b1_x2) + abs(b2_y2 - b1_y2)
    return dis + min(dis_x, dis_y)


def calculate_iou(box1, box2):
    b1_x1, b1_y1, b1_x2, b1_y2 = box1[0], box1[1], box1[2], box1[3]
    b2_x1, b2_y1, b2_x2, b2_y2 = box2[0], box2[1], box2[2], box2[3]
    # 不相交直接退出检测
    if b1_x2 < b2_x1 or b1_x1 > b2_x2 or b1_y2 < b2_y1 or b1_y1 > b2_y2:
        return 0.0
    # 计算交集
    inter_x1 = max(b1_x1, b2_x1)
    inter_y1 = max(b1_y1, b2_y1)
    inter_x2 = min(b1_x2, b2_x2)
    inter_y2 = min(b1_y2, b2_y2)
    i_area = max(0, inter_x2 - inter_x1) * max(0, inter_y2 - inter_y1)

    # 计算并集
    b1_area = (b1_x2 - b1_x1) * (b1_y2 - b1_y1)
    b2_area = (b2_x2 - b2_x1) * (b2_y2 - b2_y1)
    u_area = b1_area + b2_area - i_area

    # 避免除零错误，如果区域小到乘积为0,认为是错误识别，直接去掉
    if u_area == 0:
        return 1
        # 检查完全包含
    iou = i_area / u_area
    return iou


def caculate_single_axis_iou(box_1, box_2, axis='x'):
    b1_x1, b1_y1, b1_x2, b1_y2 = box_1
    b2_x1, b2_y1, b2_x2, b2_y2 = box_2
    if axis == 'x':
        i_min = max(b1_x1, b2_x1)
        i_max = min(b1_x2, b2_x2)
        u_area = max(b1_x2, b2_x2) - min(b1_x1, b2_x1)
    else:
        i_min = max(b1_y1, b2_y1)
        i_max = min(b1_y2, b2_y2)
        u_area = max(b1_y2, b2_y2) - min(b1_y1, b2_y1)
    i_area = max(i_max - i_min, 0)
    if u_area == 0:
        return 1
    return i_area / u_area


def caculate_single_axis_iou_ignore_axis_start(box_1, box_2, axis='x'):
    b1_x1, b1_y1, b1_x2, b1_y2 = box_1
    b2_x1, b2_y1, b2_x2, b2_y2 = box_2
    if axis == 'x':
        b1_len = b1_x2 - b1_x1
        b2_len = b2_x2 - b2_x1
    else:
        b1_len = b1_y2 - b1_y1
        b2_len = b2_y2 - b2_y1
    i_area = min(b1_len, b2_len)
    u_area = max(b1_len, b2_len)
    if u_area == 0:
        return 1
    return i_area / u_area


# 将包含关系和重叠关系的box进行过滤，只保留一个
def filter_consecutive_boxes(layout_boxes: list[LayoutBox], iou_threshold=0.92) -> (list[LayoutBox], list[int]):
    """
    检测布局框列表中包含关系和重叠关系，只保留一个
    LayoutBox.bbox: (xmin,ymin,xmax,ymax)
    """
    idx = set()
    if len(layout_boxes) <= 1:
        return layout_boxes
    for i, layout_box in enumerate(layout_boxes):
        if i in idx:
            continue
        box1 = layout_box.bbox
        for j, layout_box2 in enumerate(layout_boxes):
            if i == j or j in idx:
                continue
            box2 = layout_box2.bbox
            # 重叠过多时，选择置信度高的一个
            if calculate_iou(box1, box2) > iou_threshold:
                if layout_box.score > layout_box2.score:
                    idx.add(i)
                else:
                    idx.add(j)
                continue
            # 包含关系只保留大的识别框
            contained_box_idx = is_contained(box1, box2)
            if contained_box_idx == 1 and (
                    layout_box.score >= layout_box2.score or layout_box.label == layout_box2.label):
                idx.add(i)
                break
            elif contained_box_idx == 2 and (
                    layout_box.score <= layout_box2.score or layout_box.label == layout_box2.label):
                idx.add(j)

    return [layout_box for i, layout_box in enumerate(layout_boxes) if i not in idx]


def filter_ocr_consecutive_boxes(layout_boxes, is_poly=False, is_ocr_box=False, iou_threshold=0.92):
    """
    检测布局框列表中包含关系和重叠关系，只保留一个
    layout_boxes: shape:(num,4,2)
    """
    idx = set()
    if len(layout_boxes) <= 1:
        return layout_boxes
    for i, layout_box in enumerate(layout_boxes):
        if i in idx:
            continue
        box1 = layout_box
        if is_ocr_box:
            box1 = [layout_box[0][0], layout_box[0][1], layout_box[2][0], layout_box[2][1]]
        for j, layout_box2 in enumerate(layout_boxes):
            if i == j or j in idx:
                continue
            box2 = layout_box2
            if is_ocr_box:
                box2 = [layout_box2[0][0], layout_box2[0][1], layout_box2[2][0], layout_box2[2][1]]
            # 重叠过多时，选择面积大的
            if calculate_iou(box1, box2) > iou_threshold:
                box1_area = (box1[2] - box1[0]) * (box1[3] - box1[1])
                box2_area = (box2[2] - box2[0]) * (box2[3] - box2[1])
                if box1_area > box2_area:
                    idx.add(j)
                else:
                    idx.add(i)
                continue
            # 包含关系只保留大的识别框
            contained_box_idx = is_contained(box1, box2)
            if contained_box_idx == 1:
                idx.add(i)
                break
            elif contained_box_idx == 2:
                idx.add(j)

    return idx


# def extract_tile_from_other_labels(layout_boxes: list[LayoutBox], iou=0.8):
#     """
#     基于一个假设，如果title出现在非text的识别框里，那么一定是识别有问题，直接在后续流程进行覆盖就可以
#     :param layout_boxes:
#     :return:
#     """
#     del_idx = []
#     # 1. 筛选出 title 标签
#     titles = [box for box in layout_boxes if box.label == 'title']
#
#     # 2. 找到普通文本的边界框
#     other_boxes = [box for box in layout_boxes if box.label == 'text']
#
#     # 3. 裁剪边界框
#     for i, box in enumerate(other_boxes):
#         # 检查当前 box 是否包含任何 title
#         for title in titles:
#             if caculate_y_iou(box.bbox, title.bbox) > iou:
#                 del_idx.append(i)
#                 # title.bbox = numpy.array(title.bbox[0], title.bbox[1], title.bbox[2], title.bbox[3]))
#                 break
#             if is_contained(box.bbox, title.bbox) == 1:
#                 # 更新 box 的 ymin 和 ymax
#                 box.bbox = numpy.array((box.bbox[0], max(box.bbox[1], title.bbox[3]), box.bbox[2], box.bbox[3]))
#
#     for i in reversed(del_idx):
#         del layout_boxes[i]
#     return layout_boxes

def box_4_1_poly_to_box_4_2(poly_box):
    xmin, ymin, xmax, ymax = tuple(poly_box)
    return [[xmin,ymin], [xmax,ymin], [xmax,ymax], [xmin,ymax]]

def box_4_2_poly_to_box_4_1(poly_box):
    """
    将poly_box转换为box_4_1
    :param poly_box:
    :return:
    """
    return [poly_box[0][0], poly_box[0][1], poly_box[2][0], poly_box[2][1]]

def sorted_ocr_boxes(dt_boxes: np.ndarray | list):
    """
    Sort text boxes in order from top to bottom, left to right
    args:
        dt_boxes(array):detected text boxes with shape [4, 2]
    return:
        sorted boxes(array) with shape [4, 2]
    """
    num_boxes = len(dt_boxes)
    # Pair each box with its original index
    indexed_boxes = [(box, idx) for idx, box in enumerate(dt_boxes)]

    # Initial sort by y then x coordinates, keeping track of original indices
    sorted_boxes_with_idx = sorted(indexed_boxes, key=lambda x: (x[0][0][1], x[0][0][0]))

    # Unpack the sorted boxes and their indices
    _boxes, indices = zip(*sorted_boxes_with_idx)
    indices = list(indices)
    _boxes = [dt_boxes[i] for i in indices]
    # Perform secondary sorting within the same row
    for i in range(num_boxes - 1):
        for j in range(i, -1, -1):
            cur_box = (_boxes[j][0][0], _boxes[j][0][1], _boxes[j][2][0], _boxes[j][2][1])
            next_box = (_boxes[j + 1][0][0], _boxes[j + 1][0][1], _boxes[j + 1][2][0], _boxes[j + 1][2][1])

            # Check if boxes are in the same row and need reordering
            c_idx = is_single_axis_contained(cur_box, next_box, axis='y')
            # iou = caculate_single_axis_iou(cur_box, next_box, axis='y')
            if c_idx is not None and _boxes[j + 1][0][0] < _boxes[j][0][0]:
                # Swap boxes and their indices
                temp_box = _boxes[j + 1].copy()
                _boxes[j + 1] = _boxes[j]
                _boxes[j] = temp_box
                temp_idx = indices[j + 1]
                indices[j + 1] = indices[j]
                indices[j] = temp_idx
            else:
                break

    return _boxes, indices


def sorted_layout_boxes(res: list[LayoutBox], w):
    """
    Sort text boxes in order from top to bottom, left to right
    args:
        res(list):ppstructure results
    return:
        sorted results(list)
    """
    boxes_type = 'single'
    # res = [layout_boxes[i].bbox.bbox for i in range(len(layout_boxes))]
    num_boxes = len(res)
    if num_boxes <= 1:
        # res[0]["layout"] = "single"
        return boxes_type, res

    sorted_boxes = sorted(res, key=lambda x: (x.bbox[1], x.bbox[0]))
    _boxes = list(sorted_boxes)

    new_res = []
    res_left = []
    res_right = []
    i = 0

    while i < num_boxes:
        box_len = max(0, _boxes[i].bbox[2] - _boxes[i].bbox[0])
        if box_len == 0:
            new_res += res_left
            new_res += res_right
            new_res.append(_boxes[i])
            res_left = []
            res_right = []
            i += 1
            continue
        if i >= num_boxes:
            break
        if i == num_boxes - 1:
            if (
                    _boxes[i].bbox[1] > _boxes[i - 1].bbox[3]
                    and _boxes[i].bbox[0] < w / 2
                    and _boxes[i].bbox[2] > w / 2
            ):
                new_res += res_left
                new_res += res_right
                new_res.append(_boxes[i])
            else:
                if _boxes[i].bbox[2] > w / 2:
                    boxes_type = 'double'
                    res_right.append(_boxes[i])
                    new_res += res_left
                    new_res += res_right
                elif _boxes[i].bbox[0] < w / 2:
                    res_left.append(_boxes[i])
                    boxes_type = 'double'
                    new_res += res_left
                    new_res += res_right
            # res_left = []
            # res_right = []
            break
        #   box两边距离中线偏移不大，则认为是居中的布局
        elif _boxes[i].bbox[0] < w / 2 and _boxes[i].bbox[2] > w / 2 and (
                _boxes[i].bbox[2] - w / 2) / box_len < 0.65 and (w / 2 - _boxes[i].bbox[0]) / box_len < 0.65:
            new_res += res_left
            new_res += res_right
            new_res.append(_boxes[i])
            res_left = []
            res_right = []
            i += 1
        elif _boxes[i].bbox[0] < w / 4 and _boxes[i].bbox[2] < 3 * w / 4:
            res_left.append(_boxes[i])
            boxes_type = 'double'
            i += 1
        elif _boxes[i].bbox[0] > w / 4 and _boxes[i].bbox[2] > w / 2:
            res_right.append(_boxes[i])
            boxes_type = 'double'
            i += 1
        else:
            new_res += res_left
            new_res += res_right
            new_res.append(_boxes[i])
            res_left = []
            res_right = []
            i += 1
    return boxes_type, new_res


def handle_page_inner_box_merge(label_boxes: list[LayoutBox], x_iou=0.8, height_limit=20):
    """
    将多列pdf可能导致的文本或表格分段整合成一个merge_box
    """
    if len(label_boxes) <= 1:
        return label_boxes
    del_idx = -1
    for i in range(len(label_boxes) - 1):
        cur = label_boxes[i]
        next = label_boxes[i + 1]
        cur_box_len = cur.bbox[2] - cur.bbox[0]
        cur_box_height = cur.bbox[3] - cur.bbox[1]
        next_box_height = next.bbox[3] - next.bbox[1]
        # 太长了会影响整体的识别效果,两边x都没对齐，也不能合并
        if caculate_single_axis_iou_ignore_axis_start(cur.bbox, next.bbox) < x_iou:
            continue
        # 非表格类型，太长了就别硬拼接了，只有表格类型，需要做强识别
        if cur.label != 'table' and next.label != 'table' and next_box_height + cur_box_height > height_limit:
            continue
        if 'caption' in cur.label or 'caption' in next.label:
            continue
        if next.label == 'title':
            continue
        # 类型为表格或普通文本，且当前检测框与下一个检测框之间的距离大于当前检测框长度
        if next.bbox[0] - cur.bbox[0] > cur_box_len:
            merge_label_box = LayoutBox(label=cur.label, score=cur.score, bbox=cur.bbox, box_type='merge',
                                        merged_bbox=[cur.bbox, next.bbox])
            label_boxes[i] = merge_label_box
            del_idx = i + 1
            break
    if del_idx > 0:
        del label_boxes[del_idx]


def handle_page_between_box_merge(all_label_boxes, x_iou=0.8, height_limit=100):
    # del_idx = []
    for i in range(len(all_label_boxes) - 1):
        if len(all_label_boxes[i]) == 0 or len(all_label_boxes[i + 1]) == 0:
            continue
        cur = all_label_boxes[i][-1]
        next = all_label_boxes[i + 1][0]
        cur_box_height = cur.bbox[3] - cur.bbox[1]
        next_box_height = next.bbox[3] - next.bbox[1]
        if caculate_single_axis_iou_ignore_axis_start(cur.bbox, next.bbox) < x_iou:
            continue
        if cur.label != 'table' and next.label != 'table' and next_box_height + cur_box_height > height_limit:
            continue
        if 'caption' in cur.label or 'caption' in next.label:
            continue
        if next.label == 'title':
            continue
        merge_label_box = LayoutBox(label=cur.label, score=cur.score, bbox=cur.bbox, box_type='merge',
                                    merged_bbox=[cur.bbox, next.bbox])
        all_label_boxes[i][-1] = merge_label_box
        all_label_boxes[i + 1].pop(0)


def fix_y_axis_if_contained(cur, next, iou_threshold=0.8):
    cur_ymin, cur_ymax = cur[0][1], cur[2][1]
    next_ymin, next_ymax = next[0][1], next[2][1]
    i_y_min = max(cur_ymin, next_ymin)
    i_y_max = min(cur_ymax, next_ymax)
    i_y = max(i_y_max - i_y_min, 0)
    cur_iou = i_y / (cur_ymax - cur_ymin)
    next_iou = i_y / (next_ymax - next_ymin)
    if cur_iou >= iou_threshold:
        cur[0][1] = next[0][1]
        cur[1][1] = next[0][1]
        cur[2][1] = next[2][1]
        cur[3][1] = next[2][1]
        return True
    elif next_iou >= iou_threshold:
        next[0][1] = cur[0][1]
        next[1][1] = cur[0][1]
        next[2][1] = cur[2][1]
        next[3][1] = cur[2][1]
        return True
    return False


def extract_pages_with_metadata(input_pdf_path, output_pdf_path, from_page=0, to_page=10):
    """
    从源PDF中提取前10页并保存为新的PDF文件，同时保留书签和其他元数据。

    :param input_pdf_path: 输入PDF文件的路径
    :param output_pdf_path: 输出PDF文件的路径
    """
    # 打开源PDF文件
    doc = fitz.open(input_pdf_path)

    # 创建一个新的PDF文档用于保存提取的页面
    new_doc = fitz.Document()

    # 复制到新文档
    new_doc.insert_pdf(doc, from_page=from_page, to_page=to_page)

    # 复制书签
    # new_doc.set_toc(doc.get_toc())

    # 复制其他元数据
    new_doc.metadata = doc.metadata

    # 保存新的PDF文档
    new_doc.save(output_pdf_path)
    new_doc.close()  # 关闭新文档
    doc.close()  # 关闭原文档


def load_pdf_fitz(pdf_path, dpi=72):
    images = []
    doc = fitz.open(pdf_path)
    for i in range(len(doc)):
        page = doc[i]
        pix = page.get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72))
        image = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)

        # if width or height > 3000 pixels, don't enlarge the image
        if pix.width > 3000 or pix.height > 3000:
            pix = page.get_pixmap(matrix=fitz.Matrix(1, 1), alpha=False)
            image = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)

        # images.append(image)
        images.append(np.array(image)[:, :, ::-1])
    return images


def load_pdf_fitz_with_img_return(pdf_path, dpi=72, start_page=0, end_page=10000):
    images = []
    ori_images = []
    doc = fitz.open(pdf_path)
    toc = doc.get_toc()
    for i in range(start_page, min(end_page + 1, len(doc))):
        page = doc[i]
        pix = page.get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72))
        image = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)

        # if width or height > 3000 pixels, don't enlarge the image
        if pix.width > 3000 or pix.height > 3000:
            pix = page.get_pixmap(matrix=fitz.Matrix(1, 1), alpha=False)
            image = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)

        ori_images.append(image)
        images.append(np.array(image)[:, :, ::-1])
    return ori_images, images, toc


def load_pdf_data_fitz_with_img_return(pdf_data, dpi=72, start_page=0, end_page=10000):
    images = []
    ori_images = []
    # 使用 BytesIO 创建一个临时文件来保存 PDF 数据
    with fitz.open(stream=pdf_data, filetype="pdf") as doc:
        for i in range(start_page, min(end_page + 1, len(doc))):
            page = doc[i]
            pix = page.get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72))
            image = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)

            # 如果宽度或高度 > 3000 像素，则不放大图像
            if pix.width > 3000 or pix.height > 3000:
                pix = page.get_pixmap(matrix=fitz.Matrix(1, 1), alpha=False)
                image = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)

            ori_images.append(image)
            images.append(np.array(image)[:, :, ::-1])
        return ori_images, images, doc.get_toc()
