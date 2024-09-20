import json
import re

from mistune import BlockState, Markdown
from mistune.plugins.table import table

from utils.file_util import get_output_dir, get_output_path
from utils.img_helper import download_image, get_image_size
from utils.output_helper import LoaderOutPutEncoder, LoaderText, LoaderImage, LoaderTable
fenced_re = re.compile(r'^[`~]+', re.M)


class MarkdownLoader:
    def indent(self, text, prefix):
        return prefix + text.replace('\n', '\n' + prefix)

    def _get_fenced_marker(self, code):
        found = fenced_re.findall(code)
        if not found:
            return '```'

        ticks = []  # `
        waves = []  # ~
        for s in found:
            if s[0] == '`':
                ticks.append(len(s))
            else:
                waves.append(len(s))

        if not ticks:
            return '```'

        if not waves:
            return '~~~'
        return '`' * (max(ticks) + 1)

    def __init__(self, **kwargs):
        super().__init__()
        self.filename = kwargs.get('filename')
        self.debug = kwargs.get('debug', False)
        self.file = kwargs.get('file')
        if not self.filename and not self.file:
            raise ValueError('filename or file must be provided')
        self.page_number = 0
        self.min_img_height = 80
        self.min_img_width = 80
        self.image_num = 0
        self.table_num = 0
        self.title_stack = []
        self.title_level = []
        self.current_text = ""
        self.sections = []
        self.in_table = False
        self.in_list = False
        self.download_img = kwargs.get('download_img', True)
        self.parser = Markdown(renderer=self, plugins=[table])
        self.output_dir = kwargs.get('output_dir', get_output_dir(self.filename, output_dir=f'output'))


    def load_and_parse(self):
        markdown_text = self.file if self.file else self.read_markdown_file()
        # 解析Markdown文本
        self.parser(markdown_text)
        # 输出解析后的 sections 列表
        json_file_path = get_output_path(output_filename='result', output_file_ext='json',
                                         output_dir=f"{self.output_dir}/json")
        # 保存为 JSON 文件
        with open(json_file_path, "w", encoding="utf-8") as json_file:
            json.dump(self.sections, json_file, cls=LoaderOutPutEncoder, ensure_ascii=False, indent=4)

    def start_new_section(self):
        # 开始新的 section
        if len(self.current_text.strip()) > 0:
            self.sections.append(
                LoaderText(self.page_number, self.filename, self.title_stack.copy(), self.current_text.strip(),
                           self.title_level.copy()))
            self.current_text = ""

    def heading(self, token: dict[str, any], state: BlockState) -> str:
        level = token['attrs']['level']
        text = self.render_children(token, state)

        # 开始新的 section
        self.start_new_section()

        # 更新 title_stack 和 title_level
        while self.title_level and self.title_level[-1] >= level:
            self.title_stack.pop()
            self.title_level.pop()
        self.title_stack.append(text)
        self.title_level.append(level)

        return '\n\n'

    def list_item(self, token: dict[str, any], state: BlockState):
        # children = token['children']
        return self.render_children(token, state) + '\n'

    def render_referrences(self, state: BlockState):
        ref_links = state.env['ref_links']
        for key in ref_links:
            attrs = ref_links[key]
            text = '[' + attrs['label'] + ']: ' + attrs['url']
            title = attrs.get('title')
            if title:
                text += ' "' + title + '"'
            self.current_text += text + '\n'
            yield text

    def render_children(self, token, state: BlockState):
        children = token['children']
        return self.render_tokens(children, state)

    def blank_line(self, token: dict[str, any], state: BlockState) -> str:
        return '\n'

    def block_code(self, token: dict[str, any], state: BlockState) -> str:
        attrs = token.get('attrs', {})
        info = attrs.get('info', '')
        code = token['raw']
        if code and code[-1] != '\n':
            code += '\n'
        self.current_text += f"""以下是{info}类型的代码块
                                -------------------
                                {code}
                                -------------------
                              """
        return ''

    def block_quote(self, token: dict[str, any], state: BlockState) -> str:
        text = self.indent(self.render_children(token, state), '> ')
        return f"> {text}\n"

    def block_html(self, token: dict[str, any], state: BlockState) -> str:
        return token['raw']

    def inline_html(self, token: dict[str, any], state: BlockState) -> str:
        # content = token['raw']
        # if len(content) > 0:
        #     # 第一步：移除 <a name="..."></a> 形式的标签
        #     content = re.sub(
        #         r'<a\s+name\s*=\s*["\'][^"\']*["\']>\s*[\s\S]*\s*</a>|<a\s+name\s*=\s*["\'][^"\']*["\']>', '', content)
        #     # 第二步：移除 <a name="..."/> 形式的标签
        #     # content = re.sub(r'<a\s+name\s*=\s*["\'][^"\']*["\']\s*/?>', '', content)
        #     content = re.sub(r'</a>', '', content)
        #     content = re.sub(r'</a>', '', content)
        return ''

    def text(self, token: dict[str, any], state: BlockState) -> str:
        content = token['raw']
        return content

    def emphasis(self, token: dict[str, any], state: BlockState) -> str:
        return self.render_children(token, state)

    def strong(self, token: dict[str, any], state: BlockState) -> str:
        return self.render_children(token, state)

    def block_text(self, token: dict[str, any], state: BlockState) -> str:
        text = self.render_children(token, state)
        return text

    def paragraph(self, token: dict[str, any], state: BlockState) -> str:
        if len(token['children']):
            for p in token['children']:
                text = self.render_token(p, state)
                self.current_text += text
        return ''

    def list(self, token: dict[str, any], state: BlockState) -> str:
        first_list = not self.in_list
        self.in_list = True
        children = token['children']
        text = ''
        if children and len(children) > 0:
            for c in children:
                text += self.render_token(c, state)
        if first_list:
            self.current_text += text
            self.in_list = False
            return ''
        return self.render_children(token, state)

    def image(self, token: dict[str, any], state: BlockState) -> str:
        url = token['attrs']['url']
        # 开始新的 section
        self.start_new_section()
        image, width, height = None, None, None
        # 表格内的图片，不再进行后续ocr的处理
        if self.in_table:
            return 'picture: ' + url
        if self.download_img:
            image_data = download_image(url)
            # 无效的图片地址
            if image_data is None:
                return ''
            # 格式不对的图片 || 太小的图片
            image, width, height = get_image_size(image_data)
            if width is None or height is None:
                return ''
            if width < self.min_img_width or height < self.min_img_height:
                return ''
            file_path = get_output_path(output_filename=f'img_{self.image_num}', output_file_ext='png',
                                        output_dir=f"{self.output_dir}/images")
            image.save(file_path)
            self.image_num += 1
        loader_img = LoaderImage(self.page_number, self.filename, self.title_stack.copy(), self.title_level.copy(),
                                 width, height,
                                 image, url)
        self.sections.append(loader_img)
        return ''

    def table_head(self, token: dict[str, any], state: BlockState) -> str:
        text = '<thead><tr>'
        for c in token['children']:
            cell_text = self.render_token(c, state)
            if cell_text and len(cell_text.strip()) > 0:
                text += f'<th>{cell_text.strip()}</th>'
            else:
                text += '<th>-</th>'
        text += '</tr></thead>'
        return text

    def table_body(self, token: dict[str, any], state: BlockState) -> str:
        return self.render_children(token, state)

    def table_row(self, token: dict[str, any], state: BlockState) -> str:
        text = '<tr>'
        for c in token['children']:
            cell_text = self.render_token(c, state)
            if cell_text and len(cell_text.strip()) > 0:
                text += f'<td>{cell_text.strip()}</td>'
            else:
                text += '<td>-</td>'
        text += '</tr>'
        return text

    def table_cell(self, token: dict[str, any], state: BlockState) -> str:
        text = self.render_children(token, state)
        return text

    def table(self, token: dict[str, any], state: BlockState) -> str:
        first_table = not self.in_table
        self.in_table = True
        header = self.render_token(token['children'][0], state)
        body = self.render_token(token['children'][1], state)
        if not first_table:
            return header + body

        # 处理表格
        # 开始新的 section
        self.start_new_section()
        md_text = header + body
        self.sections.append(LoaderTable(self.page_number, self.filename, self.title_stack.copy(), header, md_text,
                                         self.title_level.copy()))

        # 将 Markdown 表格转换为 HTML 表格
        html_table = f"<table>\n{header}\n<tbody>\n{body}\n</tbody>\n</table>"

        # 保存 HTML 表格到文件
        output_file = get_output_path(output_file_ext='html',
                                      output_filename=f'table_{self.page_number}_{self.table_num}',
                                      output_dir=f"{self.output_dir}/tables")
        with open(output_file, "w", encoding="utf-8") as file:
            # file.write("<!DOCTYPE html>\n<html>\n<head>\n<meta charset='UTF-8'>\n</head>\n<body>\n")
            file.write(html_table)
            # file.write("\n</body>\n</html>")
            self.table_num += 1

        self.in_table = False
        return ''


    def read_markdown_file(self):
        """读取Markdown文件内容"""
        with open(self.filename, 'r', encoding='utf-8') as file:
            return file.read()


if __name__ == '__main__':
    # 指定要解析的Markdown文件路径
    filename = f'demo/mdDoc.md'  # 替换为您的文件路径
    # 创建自定义渲染器实例
    loader = MarkdownLoader(download_img=True, filename=filename)
    loader.load_and_parse()

