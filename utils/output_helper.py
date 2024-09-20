import json

from PIL.Image import Image
from bs4 import BeautifulSoup



class LoaderOutPutEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, LoaderOutPut):
            return obj.__dict__
        if isinstance(obj, Image):
            return ''
        return super().default(obj)


# class DocumentUploadResult:


class LoaderOutPut:
    def __init__(self, page_number, filename, title_stack, title_level):
        self.page_number = page_number
        self.filename = filename
        self.title_stack = title_stack.copy()
        self.title_level = title_level.copy()
        self.error = None


class LoaderTable(LoaderOutPut):
    def __init__(self, page_number, filename, title_stack, table_headers, html, title_level):
        super().__init__(page_number, filename, title_stack, title_level)
        self.type = "table"
        self.table_headers = table_headers
        self.html = html


class LoaderImage(LoaderOutPut):
    def __init__(self, page_number, filename, title_stack, title_level, width, height, img_data, url):
        super().__init__(page_number, filename, title_stack, title_level)
        self.type = "image"
        self.width = width
        self.height = height
        self.img_data = img_data
        self.url = url


class LoaderText(LoaderOutPut):
    def __init__(self, page_number, filename, title_stack, text, title_level):
        super().__init__(page_number, filename, title_stack, title_level)
        self.type = "text"
        self.text = text


class LoaderCaption(LoaderOutPut):
    def __init__(self, page_number, filename, title_stack, text, title_level, caption_type):
        super().__init__(page_number, filename, title_stack, title_level)
        self.type = caption_type
        self.text = text


def extract_table_headers(html):
    if not html:
        return []
    # 使用 BeautifulSoup 解析 HTML
    soup = BeautifulSoup(html, 'lxml')

    # 查找 <thead> 标签
    thead = soup.find('thead')

    # 如果找到了 <thead> 标签，则提取其中的文本
    if thead:
        # 找到 <thead> 中所有的 <td> 元素
        headers = thead.find_all('td')

        # 提取每个 <td> 元素的文本内容
        header_texts = [header.get_text(strip=True) for header in headers]

        return header_texts
    else:
        # 查找表格的第一行
        table = soup.find('table')
        if table:
            first_row = table.find('tr')
            if first_row:
                # 找到第一行中的所有 <th> 或 <td> 元素
                headers = first_row.find_all(['th', 'td'])

                # 提取每个元素的文本内容
                header_texts = [header.get_text(strip=True) for header in headers]

                return header_texts
