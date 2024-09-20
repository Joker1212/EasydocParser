import os


def get_output_path(doc_filename=None, output_file_ext='', output_filename='', output_dir=''):
    if doc_filename:
        base_name = os.path.basename(doc_filename)
        file_name, ext = os.path.splitext(base_name)
        ext = ext.lstrip('.')
        sub_dir = os.path.join(output_dir, f'{file_name}_{ext}')
    else:
        sub_dir = output_dir
    if not os.path.exists(sub_dir):
        os.makedirs(sub_dir)
        # 构建完整的文件路径
    return os.path.join(sub_dir, f"{output_filename}.{output_file_ext}")


def get_output_dir(doc_filename=None, suffix='', output_dir=''):
    if doc_filename:
        base_name = os.path.basename(doc_filename)
        file_name, ext = os.path.splitext(base_name)
        ext = ext.lstrip('.')
        if suffix:
            sub_dir = os.path.join(output_dir, f'{file_name}_{ext}_{suffix}')
        else:
            sub_dir = os.path.join(output_dir, f'{file_name}_{ext}')
    else:
        if suffix:
            sub_dir = os.path.join(output_dir, f'{suffix}')
        else:
            sub_dir = output_dir
    if not os.path.exists(sub_dir):
        os.makedirs(sub_dir)
        # 构建完整的文件路径
    return sub_dir


def get_file_name_replace_ext(doc_filename):
    base_name = os.path.basename(doc_filename)
    file_name, ext = os.path.splitext(base_name)
    ext = ext.lstrip('.')
    return f'{file_name}_{ext}'


if __name__ == '__main__':
    paht = get_output_dir(output_dir='chat-ai/knowdge_1/file1')
    print(paht)
