"""CLI ETL 辅助：RFC4180 CSV 读写、拒绝汇、运行清单、源画像、类型归一。

设计文档 §5.11 通用规范落实点：
- §5.11.1 解析器契约：生成与读取走合规 csv 模块（quotechar='"'，doublequote=True），
  严禁 str.split(',')；BOM 自动剔除（utf-8-sig）。
- §5.11.6 拒绝汇（C2）：坏行持久化 <dir>/<file>.rejects.csv。
- §5.11.13 运行清单（M3）：写出 .run.json（sha256 / 行数 / 参数）。
- §5.11.3 枚举 / 列表值归一；§5.11.1(M2) 单元格 Trim。
"""

import csv
import hashlib
import json
import os
from datetime import datetime
from typing import List, Optional, Tuple


# ---------------------------------------------------------------------------
# CSV 读写（RFC 4180）
# ---------------------------------------------------------------------------
def read_csv_rows(path: str, encoding: str = 'utf-8-sig', delimiter: str = ',') -> List[List[str]]:
    """读取 CSV 为二维单元格列表。utf-8-sig 自动剔除 BOM（§5.11.1）。"""
    with open(path, 'r', encoding=encoding, newline='') as f:
        reader = csv.reader(
            f, delimiter=delimiter, quotechar='"', doublequote=True, skipinitialspace=False
        )
        return [row for row in reader]


def write_seed_csv(path: str, header: List[str], rows: List[List[str]], delimiter: str = ','):
    """写出 seed CSV，强制 QUOTE_ALL 包裹每个单元格（§5.6.1 生成契约）。"""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(
            f, delimiter=delimiter, quoting=csv.QUOTE_ALL, quotechar='"', doublequote=True
        )
        w.writerow(header)
        for r in rows:
            w.writerow(r)


def sha256_of(path: str) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# 类型 / 值归一
# ---------------------------------------------------------------------------
def parse_bool(raw) -> bool:
    if isinstance(raw, bool):
        return raw
    s = str(raw).strip().lower()
    if s in ('true', '1', '是', 'yes', 'y'):
        return True
    if s in ('false', '0', '否', 'no', 'n'):
        return False
    raise ValueError(f"非布尔值: {raw!r}")


def coerce_value(raw, prop_type: str, option_list: Optional[list] = None,
                 enum_by_name: bool = False, multivalue_sep: str = ',') -> Tuple[object, Optional[str]]:
    """返回 (value, error)。复合类型（enum/enummulti/list/array/object）一律存 JSON 字符串。

    - enum:           存 option 中的 id（--enum-by-name 时按 name 反查）
    - enummulti/list: 多值单元格 → JSON 数组字符串（已是 JSON 串则原样）
    - object:         原样存 JSON 字符串
    """
    if isinstance(raw, str):
        s = raw.strip()
    else:
        s = raw
    if s == '' or s is None:
        return None, None

    try:
        if prop_type == 'int':
            return int(str(s)), None
        if prop_type == 'float':
            return float(str(s)), None
        if prop_type == 'bool':
            return 1 if parse_bool(s) else 0, None
        if prop_type in ('date', 'time'):
            return str(s), None
        if prop_type == 'enum':
            if option_list:
                if enum_by_name:
                    m = {o.get('name'): o.get('id') for o in option_list}
                    if s in m:
                        return m[s], None
                    return None, f"枚举名未命中: {s}"
                m = {o.get('id'): o.get('id') for o in option_list}
                if s in m:
                    return s, None
                return None, f"枚举 id 未命中: {s}"
            return str(s), None
        if prop_type in ('enummulti', 'list', 'array'):
            if isinstance(s, str) and s.startswith('['):
                return s, None  # 已是 JSON
            parts = [p.strip() for p in s.split(multivalue_sep) if p.strip() != '']
            if prop_type == 'enummulti' and option_list:
                m = {o.get('id'): o.get('id') for o in option_list}
                ids = []
                for p in parts:
                    if p in m:
                        ids.append(p)
                    else:
                        return None, f"枚举值未命中: {p}"
                return json.dumps(ids, ensure_ascii=False), None
            return json.dumps(parts, ensure_ascii=False), None
        if prop_type == 'object':
            return s, None
        # singlechar / longchar / text / objuser / timezone / table / innertable / enumquote
        return str(s), None
    except Exception as e:  # noqa: BLE001
        return None, f"类型转换失败({prop_type}): {e}"


# ---------------------------------------------------------------------------
# 拒绝汇（§5.11.6，C2）
# ---------------------------------------------------------------------------
class RejectStore:
    def __init__(self, csv_path: str, reject_out: Optional[str] = None):
        d = os.path.dirname(os.path.abspath(csv_path)) or '.'
        stem = os.path.splitext(os.path.basename(csv_path))[0]
        self.path = reject_out or os.path.join(d, f"{stem}.rejects.csv")
        self.rows: List[Tuple[int, list, str, str]] = []

    def add(self, lineno: int, raw_row, column: str, reason: str):
        self.rows.append((lineno, raw_row, column, reason))

    @property
    def count(self) -> int:
        return len(self.rows)

    def flush(self):
        if not self.rows:
            return
        with open(self.path, 'w', encoding='utf-8', newline='') as f:
            w = csv.writer(f, quoting=csv.QUOTE_ALL)
            w.writerow(['line_no', 'raw_row', 'failed_column', 'failed_reason'])
            for lineno, raw_row, col, reason in self.rows:
                raw = '|'.join(raw_row) if isinstance(raw_row, list) else str(raw_row)
                w.writerow([lineno, raw, col, reason])


# ---------------------------------------------------------------------------
# 运行清单（§5.11.13，M3）
# ---------------------------------------------------------------------------
def write_manifest(path: str, data: dict):
    os.makedirs(os.path.dirname(os.path.abspath(path)) or '.', exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def now_iso() -> str:
    return datetime.now().isoformat(timespec='seconds')


# ---------------------------------------------------------------------------
# 源画像（§5.11.1 预检门槛 H1）
# ---------------------------------------------------------------------------
def profile_source(header: List[str], data_rows: List[list], sample: int = 3) -> dict:
    return {
        'data_rows': len(data_rows),
        'columns': list(header),
        'sample': data_rows[:sample],
    }
