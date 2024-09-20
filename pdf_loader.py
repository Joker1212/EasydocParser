import os
import threading
import time
from typing import TYPE_CHECKING, AsyncIterator, Iterator, List, Optional

import cv2
# from langchain_core.document_loaders import BaseLoader
# from langchain_core.documents import Document
# from langchain_core.runnables import run_in_executor
# from langchain_text_splitters import TextSplitter

from models.ModelManager import ModelManager
from utils.file_util import get_output_path, get_output_dir
from utils.img_helper import get_croped_image, cross_section_paste_to_first, \
    fill_region_with_background_color, cross_section_paste_to_next, add_layout_box_to_img
from utils.output_helper import extract_table_headers, LoaderText, LoaderTable, LoaderImage, \
    LoaderOutPutEncoder, LoaderCaption
from utils.pdf_helper import *
import numpy as np

from utils.thread__pools import OCRThreadManager
from utils.title_helper import get_title_level, \
    calculate_ocr_box_weighted_character_width_and_height, calculate_word_iou, is_possible_title, is_layout_title_match
from Levenshtein import ratio as levenshtein_ratio


class PdfLoader:

    def __init__(self, **kwargs):
        self.filename = kwargs.get('filename')
        self.file = kwargs.get('file')
        self.debug = kwargs.get('debug', False)
        if not self.filename and not self.file:
            raise ValueError('filename or file must be provided')
        self.output_dir = kwargs.get('output_dir', get_output_dir(self.filename, output_dir=f'output'))
        # ../../example.pdf->example_pdf
        model_path = kwargs.get('model_path')
        self.page_start = kwargs.get('page_start', 0)
        self.page_end = kwargs.get('page_end', 10000)
        self.multi_core = kwargs.get('multi_core', False)
        self.min_img_height = 80
        self.min_img_width = 80
        # 初始化模型,只有第一次执行有用
        self.model_manager = ModelManager(model_path)
        self.title_stack = []
        self.title_level = []
        self.current_text = ''
        self.sections = []
        self.table_num = 0
        self.image_num = 0
        self.intermediate_structure = []  # 共享变量
        self.page_count = 0
        self.lock = threading.Lock()  # 添加锁
        self.ocr_thread_pool = OCRThreadManager()
        self.toc = None
        self.title_rough_search = kwargs.get('title_rough_search', False)

    def load_and_parse(self):
        # ... 保持不变 ...
        layout_json_output = get_output_path(output_filename="layout", output_file_ext='json',
                                             output_dir=f"{self.output_dir}/json")
        result_output = get_output_path(output_filename="result", output_file_ext='json',
                                        output_dir=f"{self.output_dir}/json")
        layout_output_dir = get_output_dir(output_dir=f'{self.output_dir}/layout')
        ori_layout_output_dir = get_output_dir(suffix='ori', output_dir=layout_output_dir)
        # 将pdf读取为图片+图片np数组
        if not self.file:
            img_list, img_np_list, toc = load_pdf_fitz_with_img_return(self.filename, dpi=216,
                                                                       start_page=self.page_start,
                                                                       end_page=self.page_end)
        else:
            img_list, img_np_list, toc = load_pdf_data_fitz_with_img_return(self.file, dpi=216,
                                                                            start_page=self.page_start,
                                                                            end_page=self.page_end)
        self.toc = toc
        # 初步布局识别
        doc_layout_result = self.do_parse_pdf_imgs([], img_list, img_np_list, ori_layout_output_dir)
        # 处理同页存在多列情况下的识别问题
        doc_layout_result = self.cross_column_optimize(doc_layout_result, img_list, img_np_list, layout_output_dir)
        # 处理跨页存在的识别问题
        doc_layout_result = self.cross_page_optimize(doc_layout_result, img_list, img_np_list, layout_output_dir)
        # 序列化存储
        with open(layout_json_output, 'w', encoding='utf-8') as f:
            json.dump(doc_layout_result, f, cls=LayoutBoxEncoder, ensure_ascii=False, indent=4)  #
        # 多进程处理ocr
        if self.multi_core:
            self.multi_core_ocr(doc_layout_result, img_list)
        else:
            self.single_core_ocr(doc_layout_result, img_list)
        # 单线程顺序拼接结果
        self.second_pass()
        with open(result_output, 'w', encoding='utf-8') as f:
            json.dump(self.sections, f, cls=LoaderOutPutEncoder, ensure_ascii=False, indent=4)  #
        return self.sections

    def multi_core_ocr(self, doc_layout_result, img_list):
        self.page_count = len(doc_layout_result)
        # 使用多线程加速 OCR 和其他处理

        # with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = []
        for page_no, page_res in enumerate(doc_layout_result):
            if len(page_res['layout_boxes']) == 0:
                continue
            # future = executor.submit(self.parse_page, page_no, page_res, img_list)
            future = self.ocr_thread_pool.submit(self.parse_page, page_no, page_res, img_list)
            futures.append(future)
        # 等待所有任务完成
        self.ocr_thread_pool.wait(futures)

    def  parse_page(self, page_no, page_res, img_list):
        label_boxes = page_res['layout_boxes']
        toc_info = self.get_page_range_toc(self.page_start + page_no - 1, self.page_start + page_no + 1)
        idx = 0
        toc_title_idx = 0

        for label_box in label_boxes:
            crop_img = get_croped_image(img_list[page_no], label_box.bbox, 10, (255, 255, 255))
            # crop_img = img_list[page_no]
            if label_box.label in caption_labels:
                idx, toc_title_idx = self.process_caption(label_box, crop_img, toc_info, toc_title_idx, page_no, idx)
            if label_box.label in textfile_labels:
                idx, toc_title_idx = self.process_text(label_box, crop_img, toc_info, toc_title_idx, page_no, idx)
            elif label_box.label == 'table':
                self.process_table(label_box, crop_img, page_no, idx)
                idx += 1
            elif label_box.label == 'figure':
                self.process_figure(label_box, crop_img, page_no, idx)
                idx += 1

    def process_caption(self, label_box, crop_img, toc_info, toc_title_idx, page_no, idx):
        result, _ = self.model_manager.ocr_engine(crop_img)
        # result = label_box.text_ocr_res
        all_text = ''
        if not result:
            return idx, toc_title_idx
        for part in result:
            _, text, _ = part
            if not text.strip():
                continue
            all_text += text.strip()
        if not all_text:
            return idx, toc_title_idx
        with self.lock:
            self.intermediate_structure.append({
                'label': label_box.label,
                'text': all_text,
                'crop_img': crop_img,
                'page_no': page_no,
                'idx': idx
            })
        return idx + 1, toc_title_idx

    def process_text(self, label_box, crop_img, toc_info, toc_title_idx, page_no, idx):
        result, _ = self.model_manager.ocr_engine(crop_img)
        # result = label_box.text_ocr_res
        if not result:
            return idx, toc_title_idx
        current_text = ''
        pre_width, pre_height = None, None
        word_width, word_height = None, None
        fix_y = False
        # 修正识别后的识别框y轴，因为数字识别的y轴和中文有区别，会出现"6.结论与展望"，识别排序后为[结论与展望,6.]
        for i in range(len(result)):
            for j in range(i+1, len(result)):
                fix_y = fix_y_axis_if_contained(result[i][0], result[j][0])
        # part[0]=box, box=[[xmin,ymin],[xmax,ymin],[xmax,ymax],[xmin,ymax]]
        # 先按ymin排序，再按xmin排序
        if fix_y:
            result = sorted(result, key=lambda part: (part[0][0][1], part[0][0][0]))
        for part in result:
            box, text, score = part
            if not text.strip():
                continue

            word_width, word_height = calculate_ocr_box_weighted_character_width_and_height(part)
            if not current_text.strip():
                pre_width = word_width
                pre_height = word_height
                current_text += text.strip()
                continue

            iou = calculate_word_iou(pre_width, pre_height, word_width, word_height)
            if iou > 0.8 or (label_box.label == 'title' and iou > 0.7):
                pre_width = word_width
                pre_height = word_height
                current_text += text.strip()
                continue

            # 检查是否为标题
            title_level, title_text, toc_title_idx = self.match_title_with_toc(current_text, toc_info, toc_title_idx)
            if title_text:
                self._add_title_to_intermediate_structure(title_text, title_level, crop_img, pre_width, pre_height,
                                                          page_no, idx)
                current_text = text.strip()
                idx += 1
            elif label_box.label == 'title' and is_layout_title_match(current_text):
                self._add_title_to_intermediate_structure(current_text, None, crop_img, pre_width, pre_height,
                                                          page_no, idx)
                current_text = text.strip()
                idx += 1
            elif self.title_rough_search and is_possible_title(current_text):
                self._add_title_to_intermediate_structure(current_text, None, crop_img, pre_width, pre_height,
                                                          page_no, idx)
                current_text = text.strip()
                idx += 1
            else:
                self._add_text_to_intermediate_structure(current_text, crop_img, pre_width, pre_height, page_no, idx)
                current_text = text.strip()
                idx += 1
            pre_width = word_width
            pre_height = word_height
        # 处理最后一个文本块
        if current_text:
            title_level, title_text, toc_title_idx = self.match_title_with_toc(current_text, toc_info, toc_title_idx)
            if title_text:
                self._add_title_to_intermediate_structure(title_text, title_level, crop_img, word_width, word_height,
                                                          page_no, idx)
                idx += 1
            elif label_box.label == 'title' and is_layout_title_match(current_text):
                self._add_title_to_intermediate_structure(current_text, None, crop_img, word_width, word_height,
                                                          page_no, idx)
                idx += 1
            elif self.title_rough_search and is_possible_title(current_text):
                self._add_title_to_intermediate_structure(current_text, None, crop_img, word_width, word_height,
                                                          page_no, idx)
                idx += 1
            else:
                self._add_text_to_intermediate_structure(current_text, crop_img, word_width, word_height, page_no, idx)
                idx += 1

        return idx, toc_title_idx

    def _add_title_to_intermediate_structure(self, text, level, crop_img, word_width, word_height, page_no, idx):
        with self.lock:
            self.intermediate_structure.append({
                'label': 'title',
                'text': text,
                'level': level,
                'crop_img': crop_img,
                'word_width': word_width,
                'word_height': word_height,
                'page_no': page_no,
                'idx': idx
            })

    def _add_text_to_intermediate_structure(self, text, crop_img, word_width, word_height, page_no, idx):
        with self.lock:
            self.intermediate_structure.append({
                'label': 'text',
                'text': text,
                'crop_img': crop_img,
                'word_width': word_width,
                'word_height': word_height,
                'page_no': page_no,
                'idx': idx
            })

    def process_table(self, label_box, crop_img, page_no, idx):
        table_html_str, *_ = self.model_manager.table_engine(np.array(crop_img)[:, :, ::-1])
        # table_html_str = res[0]['res']['html']
        # table_html_str = label_box.table_html
        table_headers = extract_table_headers(table_html_str)

        with self.lock:
            self.intermediate_structure.append({
                'label': label_box.label,
                'table_html_str': table_html_str,
                'table_headers': table_headers,
                'crop_img': crop_img,
                'page_no': page_no,
                'idx': idx
            })

    def process_figure(self, label_box, crop_img, page_no, idx):
        with self.lock:
            self.intermediate_structure.append({
                'label': label_box.label,
                'crop_img': crop_img,
                'page_no': page_no,
                'idx': idx
            })

    def match_title_with_toc(self, all_text, toc_info, toc_title_idx):
        for i in range(toc_title_idx, len(toc_info)):
            level, title = toc_info[i]
            if levenshtein_ratio(all_text, title) > 0.8:
                return level, title, i + 1
        return None, None, toc_title_idx

    def second_pass(self):
        # 单线程顺序更新 current_text, title_stack, 和 title_level
        self.title_stack = []
        self.title_level = []
        self.current_text = ''
        self.sections = []
        sort_ocr_res = sorted(self.intermediate_structure, key=lambda x: (x['page_no'], x['idx']))
        # 按照页面顺序遍历中间结构
        for i, page_data in enumerate(sort_ocr_res):
            label = page_data['label']
            page_no = page_data['page_no']
            crop_img = page_data['crop_img']
            if label == 'title':
                self.add_text_section(page_no)
                # 更新 title_stack 和 title_level
                text = page_data['text']
                level = page_data.get('level')
                if not level:
                    word_width, word_height = page_data['word_width'], page_data['word_height']
                    level = get_title_level(self.title_stack, word_width, word_height)
                while self.title_level and self.title_level[-1] >= level:
                    self.title_stack.pop()
                    self.title_level.pop()
                self.title_stack.append((text, level, page_data['word_width'], page_data['word_height']))
                self.title_level.append(level)

                # 清空 current_text
                self.current_text = ''
            elif label in textfile_labels:
                # 添加文本到 current_text
                self.current_text += page_data['text'] + ' '
            elif label in caption_labels:
                self.add_text_section(page_no)
                self.add_caption_section(page_no, page_data['text'], label)
            elif label == 'table' and page_data['table_html_str']:
                file_path = get_output_path(output_filename=f'table_{self.table_num}',
                                            output_file_ext='html',
                                            output_dir=f"{self.output_dir}/tables")
                crop_file_path = get_output_path(output_filename=f'table_crop_{self.table_num}',
                                                 output_file_ext='jpg',
                                                 output_dir=f"{self.output_dir}/tables/crop")
                crop_img.save(crop_file_path)
                with open(file_path, "w", encoding="utf-8") as file:
                    file.write(page_data['table_html_str'])
                # 添加表格
                self.add_text_section(page_no)
                self.add_table_section(page_no, page_data['table_headers'], page_data['table_html_str'])
                self.table_num += 1
            elif label == 'figure' and crop_img.width >= self.min_img_width and crop_img.height >= self.min_img_height:
                self.add_text_section(page_no)
                file_path = get_output_path(output_filename=f'img_{self.image_num}',
                                            output_file_ext='jpg',
                                            output_dir=f"{self.output_dir}/images")
                crop_img.save(file_path)
                # self.add_text_section(page_no)
                # 添加图像
                self.add_image_section(page_no, page_data['crop_img'], file_path)
                self.image_num += 1
        # 添加最后的文本段落
        if self.current_text:
            self.add_text_section(self.page_count - 1)

    def add_text_section(self, page_no):
        if self.current_text:
            title_text_stack = [title_info[0] for title_info in self.title_stack]
            self.sections.append(
                LoaderText(page_no, self.filename, title_text_stack, self.current_text, self.title_level.copy()))
            self.current_text = ''  # 清空 current_text

    def add_caption_section(self, page_no, text, caption_type):
        title_text_stack = [title_info[0] for title_info in self.title_stack]
        self.sections.append(
            LoaderCaption(page_no, self.filename, title_text_stack, text, self.title_level.copy(), caption_type))

    def add_table_section(self, page_no, table_headers, table_html_str):
        title_text_stack = [title_info[0] for title_info in self.title_stack]
        self.sections.append(
            LoaderTable(page_no, self.filename, title_text_stack, table_headers, table_html_str,
                        self.title_level.copy()))

    def add_image_section(self, page_no, crop_img, url):
        title_text_stack = [title_info[0] for title_info in self.title_stack]
        image_section = LoaderImage(page_no, self.filename, title_text_stack, self.title_level.copy(), crop_img.width,
                                    crop_img.height, crop_img, url)
        self.sections.append(image_section)

    def start_new_section(self, page_number, current_text, sections, title_stack, title_level):
        # 开始新的 section
        if len(current_text.strip()) > 0:
            sections.append(LoaderText(page_number, self.filename, title_stack, current_text.strip(), title_level))
        return ""

    def get_page_range_toc(self, start_page, end_page):
        if self.toc is None:
            return []
        # 遍历TOC，找到指定范围内的标题
        titles_in_range = []
        current_page = 1
        for level, title, page in self.toc:
            if start_page <= page - 1 <= end_page:
                titles_in_range.append((level, title))

            # 更新当前页码
            if page > current_page:
                current_page = page

                # 如果当前页码超过了结束页，退出循环
                if current_page > end_page:
                    break

        return titles_in_range

    def single_core_ocr(self, doc_layout_result, img_list):
        self.page_count = len(doc_layout_result)
        # 使用多线程加速 OCR 和其他处理
        for page_no, page_res in enumerate(doc_layout_result):
            if len(page_res['layout_boxes']) == 0:
                continue
            # future = executor.submit(self.parse_page, page_no, page_res, img_list)
            self.parse_page(page_no, page_res, img_list)

    # TODO 模型准确度提高，不需要做这种工程优化
    def cross_column_optimize(self, doc_layout_result, img_list, img_np_list, layout_output_dir):
        # 拼装同页的跨列数据
        need_rec = False
        for page_res in doc_layout_result:
            handle_page_inner_box_merge(page_res['layout_boxes'], x_iou=0.8, height_limit=page_res['valid_height'] + 20)
        for page_num, page_res in enumerate(doc_layout_result):
            valid_ymin, valid_ymax = page_res['valid_ymin'], page_res['valid_ymax']
            merged_idx = [i for i, layout_box in enumerate(page_res['layout_boxes']) if layout_box.box_type == 'merge']
            if len(merged_idx) != 1:
                continue
            for i in merged_idx:
                need_rec = True
                merged_layout_box = page_res['layout_boxes'][i]
                bboxes = merged_layout_box.merged_bbox
                page_img = img_list[page_num]
                page_valid_box = (0, valid_ymin, page_img.width, valid_ymax)
                stable_boxes = [layout_box.bbox for ix, layout_box in enumerate(page_res['layout_boxes']) if ix <= i]
                offset_boxes = [layout_box.bbox for ix, layout_box in enumerate(page_res['layout_boxes']) if ix > i]
                stable_boxes.insert(0, (0, 0, page_img.width, valid_ymin))
                offset_boxes.insert(0, bboxes[1])
                # offset_boxes.append((0, valid_ymax, page_img.width, page_img.height))
                # 本页两列合并的box
                cur_tuple = (page_img, page_valid_box, stable_boxes, offset_boxes, bboxes[0])
                next_tuple = (page_img, page_valid_box, stable_boxes, offset_boxes, bboxes[1])
                tuple_list = (cur_tuple, next_tuple)
                # 做图片的重绘，将分列造成的段落隔断进行组装
                cur_img, cur_valid_box, cur_stable_boxes, cur_offset_boxes, cur_box = tuple_list[0]
                next_img, next_valid_box, next_stable_boxes, next_offset_boxes, next_box = tuple_list[1]
                next_box_height = next_box[3] - next_box[1]
                cur_box_height = cur_box[3] - cur_box[1]
                background_color = (255, 255, 255)
                # 往左边的列粘贴，同时用背景色填充右边的列中next_box区域
                if cur_box_height >= next_box_height:
                    new_img, height_extend, _ = cross_section_paste_to_first(tuple_list, margin=10,
                                                                             background_color=background_color)
                    next_box[1] += height_extend
                    next_box[3] += height_extend
                    fill_region_with_background_color(new_img, [next_box], background_color)
                # 往右边的列粘贴，同时用背景色填充左边的列中cur_box区域
                else:
                    new_img, height_extend, _ = cross_section_paste_to_next(tuple_list)
                    fill_region_with_background_color(new_img, [cur_box], background_color)
                # 更新图片和图片np
                img_list[page_num] = new_img
                img_np_list[page_num] = np.array(new_img)[:, :, ::-1]
        if not need_rec:
            return doc_layout_result
        output_dir = get_output_dir(suffix='cross_column', output_dir=layout_output_dir)
        return self.do_parse_pdf_imgs([], img_list, img_np_list, output_dir)

    # TODO 模型准确度提高，不需要做这种工程优化
    def cross_page_optimize(self, doc_layout_result, img_list, img_np_list, layout_output_dir):
        if len(doc_layout_result) <= 1:
            return doc_layout_result
        need_rec = False
        all_label_boxes = [page_res['layout_boxes'] for page_res in doc_layout_result]
        handle_page_between_box_merge(all_label_boxes, x_iou=0.8,
                                      height_limit=doc_layout_result[0]['valid_height'] + 20)
        for page_num, page_res in enumerate(doc_layout_result):
            if len(page_res['layout_boxes']) == 0:
                continue
            last_box = page_res['layout_boxes'][-1]
            if last_box.box_type != 'merge':
                continue
            need_rec = True
            next_page_res = doc_layout_result[page_num + 1]
            valid_ymin, valid_ymax = page_res['valid_ymin'], page_res['valid_ymax']
            next_valid_ymin, next_valid_ymax = next_page_res['valid_ymin'], next_page_res['valid_ymax']

            bboxes = last_box.merged_bbox
            page_img = img_list[page_num]
            next_page_img = img_list[page_num + 1]
            page_valid_box = (0, valid_ymin, page_img.width, valid_ymax)
            next_page_valid_box = (0, next_valid_ymin, next_page_img.width, next_valid_ymax)

            cur_stable_boxes = [layout_box.bbox for layout_box in page_res['layout_boxes'] if layout_box is not None]
            cur_offset_boxes = []
            cur_stable_boxes.insert(0, (0, 0, page_img.width, valid_ymin))

            next_stable_boxes = [(0, 0, next_page_img.width, next_valid_ymin)]
            next_offset_boxes = [layout_box.bbox for layout_box in next_page_res['layout_boxes'] if
                                 layout_box is not None]
            next_offset_boxes.insert(0, bboxes[1])
            next_offset_boxes.append((0, next_valid_ymax, next_page_img.width, next_page_img.height))

            # 本页两列合并的box
            cur_tuple = (page_img, page_valid_box, cur_stable_boxes, cur_offset_boxes, bboxes[0])
            next_tuple = (next_page_img, next_page_valid_box, next_stable_boxes, next_offset_boxes, bboxes[1])
            tuple_list = (cur_tuple, next_tuple)
            # 做图片的重绘，将分列造成的段落隔断进行组装
            cur_img, cur_valid_box, cur_stable_boxes, cur_offset_boxes, cur_box = tuple_list[0]
            next_img, next_valid_box, next_stable_boxes, next_offset_boxes, next_box = tuple_list[1]
            next_box_height = next_box[3] - next_box[1]
            cur_box_height = cur_box[3] - cur_box[1]
            background_color = (255, 255, 255)
            # 往左边的列粘贴，同时用背景色填充右边的列中next_box区域
            if cur_box_height >= next_box_height:
                new_img, height_extend, crop_box = cross_section_paste_to_first(tuple_list)
                fill_region_with_background_color(next_img, [next_box], background_color)
                # 第一个元素被粘贴到前一张图了，这里需要删除box，为后面的图片拼接做准备
                page_res['valid_height'] += height_extend
                page_res['valid_ymax'] += height_extend
                page_res['img_H'] = new_img.height
                crop_layout_box = LayoutBox(crop_box, last_box.label, last_box.score)
                next_page_res['layout_boxes'].append(crop_layout_box)
                img_list[page_num] = new_img
                img_np_list[page_num] = np.array(new_img)[:, :, ::-1]
                img_list[page_num + 1] = next_img
                img_np_list[page_num + 1] = np.array(next_img)[:, :, ::-1]
            # 往右边的列粘贴，同时用背景色填充左边的列中cur_box区域
            else:
                new_img, height_extend, crop_box = cross_section_paste_to_next(tuple_list)
                next_page_res['valid_height'] += height_extend
                next_page_res['valid_ymax'] += height_extend
                next_page_res['img_H'] = new_img.height
                for layout_box in next_page_res['layout_boxes']:
                    layout_box.bbox[1] += height_extend
                    layout_box.bbox[3] += height_extend
                crop_layout_box = LayoutBox(crop_box, last_box.label, last_box.score)
                next_page_res['layout_boxes'].insert(0, crop_layout_box)
                fill_region_with_background_color(page_img, [cur_box], background_color)
                # 更新图片和图片np
                img_list[page_num] = page_img
                img_np_list[page_num] = np.array(page_img)[:, :, ::-1]
                img_list[page_num + 1] = new_img
                img_np_list[page_num + 1] = np.array(new_img)[:, :, ::-1]

        if not need_rec:
            return doc_layout_result
        output_dir = get_output_dir(suffix='cross_page', output_dir=layout_output_dir)
        return self.do_parse_pdf_imgs([], img_list, img_np_list, output_dir, use_ocr=True)

    def do_parse_pdf_imgs(self, doc_layout_result, img_list, img_np_list, output_dir, use_ocr = False):
        for i, img in enumerate(img_list):

            bgr_array = img_np_list[i]

            start_time = time.time()

            boxes, scores, class_names, elapse = self.model_manager.layout_engine(bgr_array)
            layout_boxes = [
                LayoutBox(box, class_name, score, 'single', None)
                for box, class_name, score in zip(boxes, class_names, scores)
            ]

            img_H, img_W = bgr_array.shape[0], bgr_array.shape[1]
            # 去掉页眉页脚以及引用
            layout_boxes = [layout_box for layout_box in layout_boxes if layout_box.label not in abandon_labels]
            # 去掉重叠的识别框
            layout_boxes = filter_consecutive_boxes(layout_boxes)
            # 阅读顺序排序
            layout_type, layout_boxes = sorted_layout_boxes(layout_boxes, img_W)
            if len(layout_boxes) == 0:
                continue
            valid_ymin = img.height
            valid_ymax = 0
            for layout_box in layout_boxes:
                valid_ymin = min(valid_ymin, layout_box.bbox[1])
                valid_ymax = max(valid_ymax, layout_box.bbox[3])
            # 补充页面信息，存储
            page_res = dict(
                layout_type=layout_type,
                layout_boxes=layout_boxes,
                img_H=img_H,
                img_W=img_W,
                page_no=i,
                valid_height=valid_ymax - valid_ymin,
                valid_ymin=valid_ymin,
                valid_ymax=valid_ymax
            )
            doc_layout_result.append(page_res)
            end_time = time.time()
            print(f'{i} done, time: {end_time - start_time}s')

            # 保存图片
            box_img_save_path = f'{output_dir}/page{i}_box.jpg'
            ori_img_save_path = f'{output_dir}/page{i}.jpg'
            img.save(ori_img_save_path)
            img_with_layout_boxes = add_layout_box_to_img(layout_boxes, ori_img_save_path)
            cv2.imwrite(box_img_save_path, img_with_layout_boxes)
        return doc_layout_result


if __name__ == '__main__':
    current_file_path = os.path.abspath(__file__)
    # 获取当前文件所在目录（即项目根目录）
    # TODO改在config里面配置
    project_root = os.path.dirname(current_file_path)
    model_path = os.path.join(project_root, 'models')
    filename = f'demo/lunwen_continue.pdf'
    with open(filename, 'rb') as file:
        data = file.read()
    buffer = BytesIO(data)
    loader = PdfLoader(model_path=model_path, filename=filename, file=buffer, multi_core=False, page_start=0,
                       page_end=10)
    # loader = PdfLoader(model_path=model_path, filename=filename, multi_core=False)
    start = time.time()
    res = loader.load_and_parse()
    end = time.time()
    print(f'time: {end - start}s')
