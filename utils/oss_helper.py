import asyncio
import io
from io import BytesIO
from typing import Sequence

from langchain_core.documents import Document

from kb_management.loader.utils.file_util import get_file_name_replace_ext
from kb_management.loader.utils.output_helper import LoaderOutPut, LoaderImage
from oss.oss_client import AsyncAliOss
import concurrent.futures


def upload_img_oss(documents: Sequence[Document], output_dir):
    def callback(future):
        results = future.result()
        for i, result in enumerate(results):
            doc_idx = idx[i]
            img_name = f'${img_names[i]}$'
            if isinstance(result, Exception):
                # 如果是异常，则记录错误并设置url为None
                print(f"Failed to upload: {result}")
                documents[doc_idx].metadata['img_url'] = None
            else:
                # 如果上传成功，则更新url字段
                documents[doc_idx].metadata['img_url'] = result
                documents[doc_idx].metadata['img_name'] = img_name
                documents[doc_idx].metadata["img_dict"] = {img_name: result}
                documents[doc_idx].metadata["img_data"] = None

    async_oss_client = AsyncAliOss()

    # 获取 AsyncAliOss 中的事件循环
    event_loop = async_oss_client._event_loop

    img_count = 0
    tasks = []
    idx = []
    img_names = []
    for i, document in enumerate(documents):
        img_data = document.metadata.get("img_data")
        if img_data:
            img_byte_arr = BytesIO()
            img_data.save(img_byte_arr, format='JPEG')
            img_name = f'file-inner-img-{img_count}'
            object_key = f'{output_dir}/images/{img_name}.jpeg'
            img_count += 1
            idx.append(i)
            img_names.append(img_name)
            img_byte_arr.seek(0)
            # 创建一个协程任务
            task = asyncio.run_coroutine_threadsafe(async_oss_client.async_put_object(object_key, img_byte_arr),
                                                    event_loop)
            tasks.append(task)

    # 等待所有任务完成
    future = asyncio.gather(*[asyncio.wrap_future(task) for task in tasks], return_exceptions=True)
    future.add_done_callback(callback)
    return future


def upload_file_oss_url(output_dir, filename, file_data):
    async_oss_client = AsyncAliOss()

    # 获取 AsyncAliOss 中的事件循环
    event_loop = async_oss_client._event_loop

    # 在 AsyncAliOss 的事件循环中运行协程
    future = asyncio.run_coroutine_threadsafe(async_oss_client.async_put_object(f'{output_dir}/{filename}', file_data),
                                              event_loop)
    return future
