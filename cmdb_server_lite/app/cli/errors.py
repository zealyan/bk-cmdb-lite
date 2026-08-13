# -*- coding: utf-8 -*-
"""CLI 共享错误类型与退出码（app/cli/errors.py）。

为何独立成模块：
- 退出码与 CliError 被主入口 app/cli/cmdb.py（``python -m app.cli.cmdb`` 的 __main__）
  与子命令模块 app/cli/auth_cmd.py 共用。
- ``python -m`` 会把 cmdb.py 当作 __main__ 再执行一份，若 CliError 定义在 cmdb.py 内，
  子命令从 ``app.cli.cmdb`` 真实名导入时会得到「第二份」类对象，导致 main() 的
  ``except CliError`` 与之类型不匹配、所有结构化错误被通用分支吞掉（退出码恒为 1）。
- 本模块是叶子模块（绝不会成为 -m 目标），只会被加载一次，从而保证单一 CliError 类，
  彻底消除上述双模块分裂问题。
"""

from typing import Optional


# 退出码（§9）
# ---------------------------------------------------------------------------
EXIT_OK = 0
EXIT_GENERAL = 1
EXIT_PARAM = 2
EXIT_DEP = 3
EXIT_EXISTS = 4
EXIT_DB = 5


class CliError(Exception):
    """带退出码的结构化错误。"""

    def __init__(self, code: int, msg: str, step: Optional[str] = None):
        self.code, self.msg, self.step = code, msg, step
        super().__init__(msg)
