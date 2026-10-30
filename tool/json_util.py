"""JSON 工具类：读取 JSON 文件并转换为 Python 对象（dict / list）。

路径基于项目根目录解析，既支持 "data/search_data.json" 这类相对路径，
也支持绝对路径；文件缺失、JSON 语法错误均给出明确中文异常。
"""

import json
from pathlib import Path
from typing import Any, List

from config.config import BASE_DIR
from tool.logger import get_logger

logger = get_logger(__name__)


class JsonUtil:
    """JSON 读取工具。"""

    @staticmethod
    def resolve_path(file_path: str) -> Path:
        """把相对路径解析为基于项目根目录的绝对路径。"""
        path = Path(file_path)
        return path if path.is_absolute() else BASE_DIR / path

    @classmethod
    def load(cls, file_path: str) -> Any:
        """读取 JSON 文件并返回 Python 对象。

        :raises FileNotFoundError: 文件不存在
        :raises ValueError: JSON 语法错误
        """
        path = cls.resolve_path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"JSON 文件不存在：{path}")
        if not path.is_file():
            raise ValueError(f"JSON 路径不是文件：{path}")

        try:
            with path.open(encoding="utf-8") as file:
                data = json.load(file)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"JSON 解析失败：{path}（第 {exc.lineno} 行第 {exc.colno} 列：{exc.msg}）"
            ) from exc

        logger.info("读取 JSON 成功：%s", path)
        return data

    @classmethod
    def load_list(cls, file_path: str, key: str = None) -> List[dict]:
        """读取 JSON 并返回列表，常用于参数化数据。

        :param key: 若 JSON 为 dict，则取该 key 对应的列表
        """
        data = cls.load(file_path)

        if key is not None:
            if not isinstance(data, dict) or key not in data:
                raise ValueError(f"JSON 中不存在 key：{key!r}（文件：{file_path}）")
            data = data[key]

        if not isinstance(data, list):
            raise ValueError(f"JSON 顶层结构不是列表：{file_path}")

        logger.info("JSON 列表读取成功，共 %s 条：%s", len(data), file_path)
        return data
