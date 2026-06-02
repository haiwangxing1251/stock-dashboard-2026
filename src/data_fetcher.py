"""
股市数据抓取模块
==================
基于 AKShare 抓取 A 股行情数据，零 API Key。

支持:
- 主要指数实时行情
- 个股实时行情（自选股）
- 板块涨跌排名
- 北向资金流向
"""

import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any


def _ensure_akshare():
    """确保 akshare 可用"""
    try:
        import akshare as ak
        return ak
    except ImportError:
        print("正在安装 akshare ...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "akshare", "-q"])
        import akshare as ak
        return ak


def fetch_index_realtime() -> List[Dict]:
    """获取 A 股主要指数实时行情"""
    ak = _ensure_akshare()
    results = []

    try:
        df = ak.stock_zh_index_spot_em()
        # 目标指数代码
        targets = {
            "上证指数": "000001",
            "深证成指": "399001",
            "创业板指": "399006",
            "科创50": "000688",
            "沪深300": "000300",
            "上证50": "000016",
            "中证500": "000905",
            "中证1000": "000852",
        }
        for _, row in df.iterrows():
            code = str(row.get("代码", ""))
            for name, target_code in targets.items():
                if code == target_code:
                    results.append({
                        "name": name,
                        "code": code,
                        "price": float(row.get("最新价", 0) or 0),
                        "change_pct": float(row.get("涨跌幅", 0) or 0),
                        "change_amt": float(row.get("涨跌额", 0) or 0),
                        "volume": float(row.get("成交量", 0) or 0),
                        "amount": float(row.get("成交额", 0) or 0),
                    })
                    break
    except Exception as e:
        print(f"[指数行情] 抓取失败: {e}")

    return results


def fetch_stock_realtime(codes: List[str]) -> List[Dict]:
    """
    获取个股实时行情

    Args:
        codes: 股票代码列表，如 ["600519", "000858"]
    """
    ak = _ensure_akshare()
    results = []

    try:
        df = ak.stock_zh_a_spot_em()
        for _, row in df.iterrows():
            code = str(row.get("代码", ""))
            if code in codes:
                results.append({
                    "name": str(row.get("名称", "")),
                    "code": code,
                    "price": float(row.get("最新价", 0) or 0),
                    "change_pct": float(row.get("涨跌幅", 0) or 0),
                    "change_amt": float(row.get("涨跌额", 0) or 0),
                    "volume": float(row.get("成交量", 0) or 0),
                    "amount": float(row.get("成交额", 0) or 0),
                    "turnover_rate": float(row.get("换手率", 0) or 0),
                    "pe": float(row.get("市盈率-动态", 0) or 0),
                    "pb": float(row.get("市净率", 0) or 0),
                    "high": float(row.get("最高", 0) or 0),
                    "low": float(row.get("最低", 0) or 0),
                    "open": float(row.get("今开", 0) or 0),
                    "prev_close": float(row.get("昨收", 0) or 0),
                })
    except Exception as e:
        print(f"[个股行情] 抓取失败: {e}")

    return results


def fetch_sector_ranking(limit: int = 20) -> List[Dict]:
    """获取行业板块涨跌排名（Top N）"""
    ak = _ensure_akshare()
    results = []

    try:
        df = ak.stock_board_industry_name_em()
        for _, row in df.head(limit).iterrows():
            results.append({
                "name": str(row.get("板块名称", "")),
                "code": str(row.get("板块代码", "")),
                "change_pct": float(row.get("涨跌幅", 0) or 0),
            })
    except Exception as e:
        print(f"[板块排名] 抓取失败: {e}")

    return results


def fetch_north_flow(days: int = 5) -> List[Dict]:
    """获取北向资金近期流向"""
    ak = _ensure_akshare()
    results = []

    try:
        # akshare 1.18+ 接口名称可能变化，尝试多种接口
        for func_name in ["stock_hsgt_north_net_flow_in_em", "stock_em_hsgt_north_net_flow_in"]:
            if hasattr(ak, func_name):
                df = getattr(ak, func_name)(symbol="北向资金")
                for _, row in df.head(days).iterrows():
                    results.append({
                        "date": str(row.iloc[0]) if len(row) > 0 else "",
                        "net_buy": float(row.iloc[1]) if len(row) > 1 else 0,
                    })
                break
        else:
            print(f"[北向资金] 接口不可用，尝试备用接口...")
            # 备用：沪股通+深股通合计
            for func_name2 in ["stock_hsgt_north_cash_em", "stock_em_hsgt_north_cash"]:
                if hasattr(ak, func_name2):
                    df = getattr(ak, func_name2)(symbol="北向")
                    for _, row in df.head(days).iterrows():
                        results.append({
                            "date": str(row.iloc[0]) if len(row) > 0 else "",
                            "net_buy": float(row.iloc[1]) if len(row) > 1 else 0,
                        })
                    break
    except Exception as e:
        print(f"[北向资金] 抓取失败: {e}")

    return results


def fetch_market_overview() -> Dict[str, Any]:
    """获取市场整体概况"""
    ak = _ensure_akshare()
    overview = {
        "total_up": 0,
        "total_down": 0,
        "total_flat": 0,
        "limit_up": 0,
        "limit_down": 0,
    }

    try:
        df = ak.stock_zh_a_spot_em()
        if df is not None and len(df) > 0:
            changes = pd.to_numeric(df["涨跌幅"], errors="coerce")
            overview["total_up"] = int((changes > 0).sum())
            overview["total_down"] = int((changes < 0).sum())
            overview["total_flat"] = int((changes == 0).sum())
            overview["limit_up"] = int((changes >= 9.9).sum())
            overview["limit_down"] = int((changes <= -9.9).sum())
            overview["total_stocks"] = len(df)
    except Exception as e:
        print(f"[市场概况] 抓取失败: {e}")

    return overview


# pandas 延迟导入（akshare 依赖它）
try:
    import pandas as pd
except ImportError:
    pd = None


def fetch_all(watchlist_path: str) -> Dict[str, Any]:
    """
    一键抓取所有数据

    Args:
        watchlist_path: watchlist.json 的路径
    """
    print("=" * 50)
    print("📊 股市数据抓取启动")

    # 读取自选股列表
    watch_codes = []
    if os.path.exists(watchlist_path):
        with open(watchlist_path, "r", encoding="utf-8") as f:
            wl = json.load(f)
        watch_codes = [s["code"] for s in wl.get("自选股", [])]
        print(f"📋 自选股: {len(watch_codes)} 只")

    data = {}

    # 1. 市场概况
    print("📈 抓取市场概况...")
    data["overview"] = fetch_market_overview()

    # 2. 指数行情
    print("📊 抓取指数行情...")
    data["indices"] = fetch_index_realtime()

    # 3. 个股行情
    if watch_codes:
        print(f"🔍 抓取个股行情 ({len(watch_codes)} 只)...")
        data["stocks"] = fetch_stock_realtime(watch_codes)
    else:
        data["stocks"] = []

    # 4. 板块排名
    print("🏭 抓取板块排名...")
    data["sectors"] = fetch_sector_ranking()

    # 5. 北向资金
    print("💰 抓取北向资金...")
    data["north_flow"] = fetch_north_flow()

    # 时间戳
    beijing_tz = timezone(timedelta(hours=8))
    data["generated_at"] = datetime.now(beijing_tz).strftime("%Y-%m-%d %H:%M:%S")
    data["generated_at_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    print(f"✅ 数据抓取完成 @ {data['generated_at']}")
    print("=" * 50)

    return data


if __name__ == "__main__":
    # 测试运行
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    wl_path = os.path.join(base_dir, "data", "watchlist.json")
    data = fetch_all(wl_path)
    print(json.dumps(data, ensure_ascii=False, indent=2, default=str))
