"""
A股行情仪表盘 — 主入口
========================

供 GitHub Actions 定时调用：
  1. 从 yfinance (Yahoo Finance) 抓取最新 A 股行情数据
  2. 生成自包含 HTML 仪表盘 → docs/index.html

依赖: yfinance
无 API Key，全部免费，全球可用。
"""

import json
import os
import sys
import time

# 确保 src/ 在导入路径中
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(BASE_DIR, "src")
sys.path.insert(0, SRC_DIR)

from data_fetcher import fetch_all
from report import generate_stock_html, save_report

# ============================================================
# 路径配置
# ============================================================
DATA_DIR = os.path.join(BASE_DIR, "data")
WATCHLIST_FILE = os.path.join(DATA_DIR, "watchlist.json")
OUTPUT_FILE = os.path.join(BASE_DIR, "docs", "index.html")


def main():
    start_time = time.time()

    print("=" * 55)
    print("  A股行情仪表盘 — 数据抓取 & 报告生成")
    print("=" * 55)

    # 抓取所有数据
    data = fetch_all(WATCHLIST_FILE)

    # 把 watchlist 原始配置也传入，供前端管理面板使用
    try:
        with open(WATCHLIST_FILE, "r", encoding="utf-8") as f:
            data["watchlist_config"] = json.load(f)
    except Exception:
        data["watchlist_config"] = {}

    # 生成 HTML 报告
    print("\n📝 生成 HTML 报告...")
    html = generate_stock_html(data)

    # 保存
    save_report(html, OUTPUT_FILE)

    elapsed = time.time() - start_time
    print(f"\n✅ 全部完成，耗时 {elapsed:.1f}s")
    print(f"   数据时间: {data.get('generated_at', 'N/A')}")
    print(f"   指数数量: {len(data.get('indices', []))}")
    print(f"   个股数量: {len(data.get('stocks', []))}")
    print(f"   板块数量: {len(data.get('sectors', []))}")


if __name__ == "__main__":
    # Windows UTF-8 兼容
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    main()
