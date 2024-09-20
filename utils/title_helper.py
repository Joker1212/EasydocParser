import re

import re

weight_dict = {
    'digit': 1.0,  # 数字权重
    'english': 0.8,  # 英文权重
    'chinese': 1.8,  # 中文权重
    'english_symbol': 0.6,  # 英文符号权重
    'chinese_symbol': 1.5,  # 中文符号权重
}

def is_layout_title_match(text: str,
        title_max_word_length: int = 15,
        non_alpha_threshold: float = 0.5):
    # 文本长度为0的话，肯定不是title
    if len(text) == 0:
        return False

    # 文本中有标点符号，就不是title
    ENDS_IN_PUNCT_PATTERN = r"[^\w\s]\Z"
    ENDS_IN_PUNCT_RE = re.compile(ENDS_IN_PUNCT_PATTERN)
    if ENDS_IN_PUNCT_RE.search(text) is not None:
        # 如果是句号，则直接返回False
        if "。" in text:
            return False

    # 检查是否包含中文句号
    if '。' in text:
        return False

    # 文本长度不能超过设定值，默认20
    # NOTE(robinson) - splitting on spaces here instead of word tokenizing because it
    # is less expensive and actual tokenization doesn't add much value for the length check
    if len(text.split()) > title_max_word_length:
        return False

    # 文本中数字的占比不能太高，否则不是title
    if under_non_alpha_ratio(text, threshold=non_alpha_threshold):
        return False

    return True

def is_possible_title(
        text: str,
        title_max_word_length: int = 15,
        non_alpha_threshold: float = 0.5,
) -> bool:
    """Checks to see if the text passes all of the checks for a valid title.

    Parameters
    ----------
    text
        The input text to check
    title_max_word_length
        The maximum number of words a title can contain
    non_alpha_threshold
        The minimum number of alpha characters the text needs to be considered a title
    """

    # 文本长度为0的话，肯定不是title
    if len(text) == 0:
        return False

    # 文本中有标点符号，就不是title
    ENDS_IN_PUNCT_PATTERN = r"[^\w\s]\Z"
    ENDS_IN_PUNCT_RE = re.compile(ENDS_IN_PUNCT_PATTERN)
    if ENDS_IN_PUNCT_RE.search(text) is not None:
        # 如果是句号，则直接返回False
        if "。" in text:
            return False

    # 检查是否包含中文句号
    if '。' in text:
        return False

    # 文本长度不能超过设定值，默认20
    # NOTE(robinson) - splitting on spaces here instead of word tokenizing because it
    # is less expensive and actual tokenization doesn't add much value for the length check
    if len(text.split()) > title_max_word_length:
        return False

    # 文本中数字的占比不能太高，否则不是title
    if under_non_alpha_ratio(text, threshold=non_alpha_threshold):
        return False

    # NOTE(robinson) - Prevent flagging salutations like "To My Dearest Friends," as titles
    if text.endswith((",", "，")):
        return False

    if text.isnumeric():
        return False

    # 开头的字符内应该有数字，默认5个字符内
    if len(text) < 5:
        text_15 = text
    else:
        text_15 = text[:5]
    alpha_in_text_5 = sum(list(map(lambda x: x.isnumeric(), list(text_15))))
    if not alpha_in_text_5:
        return False

    if proj_match(text):
        return True

    # 增加对特定前缀的正则匹配
    if re.match(r"^(章节|小节|摘要|目录|结论|附录|参考文献|致谢|前言|导言)", text):
        return True

    # 检查是否以特定的后缀结尾
    if re.match(r".*(标题|标题一|标题二|标题三)$", text):
        return True

    # 新增的检查项
    # 检查是否以数字或罗马数字开头
    if re.match(r"^[0-9]+[.、]", text) or re.match(r"^[IVXLCDMivxlcdm]+[.、]", text):
        return True

    # 检查是否以括号内的序号开头
    if re.match(r"^[\(\（][0-9]+[\)\）]", text) or re.match(r"^[\(\（][IVXLCDMivxlcdm]+[\)\）]", text):
        return True

    # 检查是否以常见的列表标记开头
    if re.match(r"^[ \t]*[-*+]", text):
        return True

    # 检查首字母是否大写
    if text and text[0].isalpha() and text[0].isupper():
        return True

    return False


def proj_match(line):
    if len(line) <= 2:
        return
    if re.match(r"[0-9 ().,%%+/-]+$", line):
        return False
    for p, j in [
        (r"第[零一二三四五六七八九十百]+章", 1),
        (r"第[零一二三四五六七八九十百]+[条节]", 2),
        (r"[零一二三四五六七八九十百]+[、 　]", 3),
        (r"[\(（][零一二三四五六七八九十百]+[）\)]", 4),
        (r"[0-9]+(、|\.[　 ]|\.[^0-9])", 5),
        (r"[0-9]+\.[0-9]+(、|[. 　]|[^0-9])", 6),
        (r"[0-9]+\.[0-9]+\.[0-9]+(、|[ 　]|[^0-9])", 7),
        (r"[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+(、|[ 　]|[^0-9])", 8),
        (r".{,48}[：:?？]$", 9),
        (r"[0-9]+）", 10),
        (r"[\(（][0-9]+[）\)]", 11),
        (r"[零一二三四五六七八九十百]+是", 12),
        (r"[⚫•➢✓]", 12)
    ]:
        if re.match(p, line):
            return j
    return


def under_non_alpha_ratio(text: str, threshold: float = 0.5):
    """Checks if the proportion of non-alpha characters in the text snippet exceeds a given
    threshold. This helps prevent text like "-----------BREAK---------" from being tagged
    as a title or narrative text. The ratio does not count spaces.

    Parameters
    ----------
    text
        The input string to test
    threshold
        If the proportion of non-alpha characters exceeds this threshold, the function
        returns False
    """
    if len(text) == 0:
        return False

    alpha_count = len([char for char in text if char.strip() and char.isalpha()])
    total_count = len([char for char in text if char.strip()])
    try:
        ratio = alpha_count / total_count
        return ratio < threshold
    except:
        return False


def get_title_level(title_stack, word_width, word_height, area_threshold=0.72):
    # 从后往前遍历 title_stack
    for title_info in reversed(title_stack):
        title_text, title_level, title_word_width, title_word_height = title_info
        # min_h = min(word_height, title_word_height)
        # max_h = max(word_height, title_word_height)
        # min_w = min(word_width, title_word_width)
        # max_w = max(word_width, title_word_width)
        area_ratio = calculate_word_iou(title_word_height, title_word_width, word_height, word_width)
        #
        # iou = 0.6 * (min_w / max_w) + 0.2 * (min_h / max_h) + 0.2 * area_ratio
        # 检查面积是否在阈值范围内
        if area_ratio >= area_threshold:
            # 如果面积足够接近，则当前标题与之前的标题属于同一层级
            return title_level
        else:
            # 如果当前标题比之前的标题小，则当前标题的层级比之前的大一级
            if word_width < title_word_width and word_height < title_word_height:
                return title_level + 1
            else:
                # 如果当前标题比之前的标题大，则继续查找或使用默认层级
                continue

    # 如果没有匹配到任何层级，则使用默认层级
    return 1  # 默认层级为 1


def calculate_word_iou(title_word_height, title_word_width, word_height, word_width):
    # 计算面积
    current_area = word_width * word_height
    title_area = title_word_width * title_word_height
    # 计算面积的比例
    area_ratio = min(current_area, title_area) / max(current_area, title_area)
    return area_ratio


def calculate_weighted_character_width_and_height(ocr_result):
    part_width = []
    part_height = []
    for part in ocr_result:
        width, height = calculate_ocr_box_weighted_character_width_and_height(part)
        if width and height:
            part_width.append(width)
            part_height.append(height)
    if len(part_width) > 0 and len(part_height) > 0:
        return sum(part_width) / len(part_width), sum(part_height) / len(part_height)
    return None, None


def calculate_ocr_box_weighted_character_width_and_height(ocr_part):
    adjusted_word_count = 0
    box, text, score = ocr_part
    text = text.strip()
    if len(text) == 0:
        return None, None
    xmin, ymin, xmax, ymax = box[0][0], box[0][1], box[2][0], box[2][1]

    # 计算当前文本块的宽度和高度
    width = xmax - xmin
    height = ymax - ymin
    for char in text:
        weight = 1
        if char.isdigit():
            weight = weight_dict['digit']
        elif char.isalpha() and char.isascii():
            weight = weight_dict['english']
        elif '\u4e00' <= char <= '\u9fff':
            weight = weight_dict['chinese']
        elif char in "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~":  # 英文标点符号
            weight = weight_dict['english_symbol']
        elif char in '，。！？【】《》（）：；‘’“”·—…':  # 中文标点符号
            weight = weight_dict['chinese_symbol']

        # 更新调整后的字符数量

        adjusted_word_count += weight

    # 计算加权平均宽度和高度
    if adjusted_word_count > 0:
        return width / adjusted_word_count, height

# def same_title_structure(title_stack1, title_stack2):
#
