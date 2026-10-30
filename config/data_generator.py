"""数据生成工具：模拟姓名、手机号、身份证号。

身份证号按 GB 11643-1999 生成：6 位地区码 + 8 位出生日期 + 3 位顺序码 + 1 位校验码，
校验码采用 ISO 7064:1983 MOD 11-2 算法，可直接用于表单校验类用例。
"""

import random
from datetime import date, timedelta

# 常用地区码（行政区划前 6 位）
AREA_CODES = [
    "110101",  # 北京东城
    "310101",  # 上海黄浦
    "440305",  # 深圳南山
    "330106",  # 杭州西湖
    "510107",  # 成都武侯
    "420106",  # 武汉武昌
    "320102",  # 南京玄武
    "370102",  # 济南历下
]

# 常见姓氏与名字用字，组合出自然的中文姓名
SURNAMES = "赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何吕施张孔曹严华金魏陶姜"
GIVEN_CHARS = "伟芳娜秀英敏静丽强磊军洋勇艳杰娟涛明超秀霞平刚桂英欣怡子轩浩然雨桐"

# 身份证校验码：加权和 % 11 -> 校验字符
CHECK_CODES = "10X98765432"
WEIGHTS = (7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2)

# 手机号号段：1[3-9] 开头，共 11 位
PHONE_PREFIXES = ("130", "131", "132", "133", "135", "136", "137", "138", "139",
                  "150", "151", "152", "153", "155", "156", "157", "158", "159",
                  "180", "181", "182", "183", "185", "186", "187", "188", "189",
                  "176", "177", "178", "199")


def generate_name() -> str:
    """生成 2~3 位的中文姓名。"""
    surname = random.choice(SURNAMES)
    given_len = random.choice((1, 2, 2))
    given = "".join(random.choice(GIVEN_CHARS) for _ in range(given_len))
    return f"{surname}{given}"


def generate_phone() -> str:
    """生成 11 位手机号，符合 1[3-9] 开头规则。"""
    return random.choice(PHONE_PREFIXES) + "".join(str(random.randint(0, 9)) for _ in range(8))


def _random_birthday(start_year: int = 1960, end_year: int = 2005) -> date:
    """在指定年份区间内随机生成一个合法日期。"""
    start = date(start_year, 1, 1)
    end = date(end_year, 12, 31)
    return start + timedelta(days=random.randint(0, (end - start).days))


def calc_check_code(body: str) -> str:
    """根据身份证前 17 位计算校验码。"""
    if len(body) != 17 or not body.isdigit():
        raise ValueError(f"计算校验码需要 17 位数字，收到：{body!r}")
    total = sum(int(digit) * weight for digit, weight in zip(body, WEIGHTS))
    return CHECK_CODES[total % 11]


def is_valid_id_card(id_card: str) -> bool:
    """校验 18 位身份证号（长度、位次字符、出生日期、校验码）。"""
    if len(id_card) != 18:
        return False
    if not id_card[:17].isdigit() or id_card[17] not in CHECK_CODES:
        return False
    try:
        date(int(id_card[6:10]), int(id_card[10:12]), int(id_card[12:14]))
    except ValueError:
        return False  # 出生日期非法
    return calc_check_code(id_card[:17]) == id_card[17]


def generate_id_card() -> str:
    """生成 18 位身份证号，校验位按国家标准计算。"""
    area = random.choice(AREA_CODES)
    birthday = _random_birthday().strftime("%Y%m%d")
    # 顺序码第 3 位奇数为男、偶数为女
    sequence = f"{random.randint(0, 99):02d}{random.choice((1, 3, 5, 7, 9))}"
    body = f"{area}{birthday}{sequence}"
    return body + calc_check_code(body)


def generate_user() -> dict:
    """一次生成完整用户资料，便于表单类用例直接参数化。"""
    return {
        "name": generate_name(),
        "phone": generate_phone(),
        "id_card": generate_id_card(),
    }
