"""
代码节点示例：将传入对象转成字符串

使用方法：
1. 在代码节点的"输入变量"中配置需要转换的变量
2. 变量会通过 input 对象传入
3. 输出结果存储在 output 对象中

示例输入变量配置：
- name: data, source: ${start.question}

支持的输入类型：
- 字典 (dict)
- 列表 (list)
- 字符串 (str)
- 数字 (int/float)
- 对象 (object)
"""

import json

def main(input_data):
    """
    将传入的对象转换为字符串

    Args:
        input_data: 输入数据对象，包含配置的输入变量

    Returns:
        output: 包含转换后的字符串结果
    """
    # 获取输入变量（根据配置的变量名获取）
    # 假设配置的输入变量名为 "data"
    data = input_data.get("data") or input_data.get("input") or input_data

    # 根据类型转换为字符串
    result = convert_to_string(data)

    # 返回结果
    output = {
        "result": result,
        "type": get_type_name(data)
    }

    return output


def convert_to_string(obj):
    """
    将任意对象转换为字符串

    Args:
        obj: 任意类型的对象

    Returns:
        str: 字符串表示
    """
    if obj is None:
        return ""

    if isinstance(obj, str):
        return obj

    if isinstance(obj, (dict, list)):
        try:
            # 尝试 JSON 序列化，格式化输出
            return json.dumps(obj, ensure_ascii=False, indent=2)
        except Exception:
            return str(obj)

    if isinstance(obj, (int, float, bool)):
        return str(obj)

    # 其他类型直接转字符串
    return str(obj)


def get_type_name(obj):
    """
    获取对象的类型名称

    Args:
        obj: 任意对象

    Returns:
        str: 类型名称
    """
    if obj is None:
        return "null"

    type_map = {
        dict: "dict",
        list: "list",
        str: "string",
        int: "integer",
        float: "float",
        bool: "boolean",
    }

    obj_type = type(obj)
    return type_map.get(obj_type, obj_type.__name__)


# 执行入口
if __name__ == "__main__":
    # 测试用例
    test_cases = [
        {"name": "张三", "age": 25},
        ["苹果", "香蕉", "橙子"],
        "直接字符串",
        12345,
        3.14159,
        True,
        None,
    ]

    for test_data in test_cases:
        result = main({"data": test_data})
        print(f"输入类型: {result['type']}")
        print(f"输出结果:\n{result['result']}")
        print("-" * 40)