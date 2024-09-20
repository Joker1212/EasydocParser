import os
import threading
from typing import List

from lineless_table_rec import LinelessTableRecognition
from rapid_layout import RapidLayout
from rapidocr_onnxruntime import RapidOCR
import numpy as np

from utils.pdf_helper import sorted_ocr_boxes
from table_cls import TableCls
from wired_table_rec import WiredTableRecognition


class OCRModel(RapidOCR):
    # def x(self):
    #     pass
    def sorted_boxes(self, dt_boxes: np.ndarray) -> List[np.ndarray]:
        dt_boxes, _ = sorted_ocr_boxes(dt_boxes)
        return dt_boxes


class TableModel:
    def __init__(self):
        self.lineless_engine = LinelessTableRecognition()
        self.wired_engine = WiredTableRecognition()
        self.table_cls = TableCls()

    def __call__(self, img):
        cls, elasp = self.table_cls(img)
        if cls == 'wired':
            table_engine = self.wired_engine
        else:
            table_engine = self.lineless_engine
        html, elasp, polygons, logic_points, ocr_res = table_engine(img)
        return html, elasp


class ModelManager:
    """单例模式管理模型实例"""

    _instances = {}
    _lock = threading.Lock()

    def __new__(cls, model_path):
        if model_path not in cls._instances:
            with cls._lock:
                if model_path not in cls._instances:
                    cls._instances[model_path] = super(ModelManager, cls).__new__(cls)
                    # 模型路径
                    # table_model_dir = os.path.join(model_path, 'table.onnx')
                    # table_char_dict_model_dir = os.path.join(model_path, 'table_structure_dict_ch.txt')
                    det_model_dir = os.path.join(model_path, 'ch_PP-OCRv4_det_infer.onnx')
                    cls_model_dir = os.path.join(model_path, 'ch_ppocr_mobile_v2.0_cls_infer.onnx')
                    rec_model_dir = os.path.join(model_path, 'ch_PP-OCRv4_rec_infer.onnx')
                    rec_keys_model_dir = os.path.join(model_path, 'ppocr_keys_v1.txt')
                    layout_model_dir = os.path.join(model_path, 'layout_cdla.onnx')

                    kwargs = {
                        "det_model_path": det_model_dir,
                        "rec_model_path": rec_model_dir,
                        "cls_model_path": cls_model_dir,
                        "rec_keys_path": rec_keys_model_dir
                    }
                    cls._instances[model_path].ocr_engine = RapidOCR(config_path=f'{model_path}/config.yaml', **kwargs)
                    cls._instances[model_path].layout_engine = RapidLayout(conf_thres=0.2, model_path=layout_model_dir)
                    cls._instances[model_path].table_engine = TableModel()
        return cls._instances[model_path]


if __name__ == '__main__':
    path = os.path.abspath('config.yaml')
    print(path)
