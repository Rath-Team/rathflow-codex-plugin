"""MCP server 入口。

作为 `python3 -c` 引导脚本的目标被启动，也支持 `python3 server/__main__.py` 直跑
（本机自测用）。把本目录塞进 sys.path，让同目录的平铺模块能被 import。
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from server import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
