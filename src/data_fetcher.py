"""
股市数据抓取模块（全球可用版）
==============================
使用 yfinance (Yahoo Finance) 抓取 A 股行情数据，全球服务器均可访问。
内置重试机制和请求间隔，避免触发限流。
"""

import json
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any


# ============ 安全浮点转换 ============
def _safe_float(val, default=0.0):
    try:
        return float(val) if val is not None else default
    except (ValueError, TypeError):
        return default


# ============ yfinance 请求封装（带重试+延迟） ============

_YF_SESSION = None


def _get_yf_session():
    """获取或创建 yfinance session，复用连接减少限流风险"""
    global _YF_SESSION
    if _YF_SESSION is None:
        try:
            import yfinance as yf
            from requests import Session
            _YF_SESSION = Session()
            _YF_SESSION.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
        except ImportError:
            return None
    return _YF_SESSION


def _yf_history(ticker: str, retries: int = 3, delay: float = 2.0):
    """获取历史行情，带重试和延迟"""
    import yfinance as yf
    for attempt in range(retries):
        try:
            t = yf.Ticker(ticker, session=_get_yf_session())
            hist = t.history(period="5d", interval="1d")
            if hist is not None and len(hist) >= 1:
                return hist
        except Exception as e:
            err_msg = str(e).lower()
            if "too many requests" in err_msg or "rate" in err_msg:
                wait = delay * (attempt + 1) * 2
                print(f"    ⏳ {ticker} 限流，等待 {wait}s 后重试...")
                time.sleep(wait)
            else:
                print(f"    ⚠️ {ticker} 请求失败: {str(e)[:80]}")
                time.sleep(delay)
    return None


def _yf_info(ticker: str, retries: int = 2, delay: float = 1.5):
    """获取 ticker info，带重试"""
    import yfinance as yf
    for attempt in range(retries):
        try:
            t = yf.Ticker(ticker, session=_get_yf_session())
            return t.info
        except Exception as e:
            err_msg = str(e).lower()
            if "too many requests" in err_msg or "rate" in err_msg:
                time.sleep(delay * (attempt + 1) * 2)
            else:
                time.sleep(delay)
    return {}


# ============ 指数行情 ============

INDEX_MAP = {
    "000001.SS": {"name": "上证指数", "code": "000001"},
    "399001.SZ": {"name": "深证成指", "code": "399001"},
    "399006.SZ": {"name": "创业板指", "code": "399006"},
    "000688.SS": {"name": "科创50", "code": "000688"},
    "000300.SS": {"name": "沪深300", "code": "000300"},
    "000016.SS": {"name": "上证50", "code": "000016"},
}


def fetch_index_yahoo() -> List[Dict]:
    """通过 yfinance 获取指数行情"""
    results = []
    for ticker, meta in INDEX_MAP.items():
        try:
            hist = _yf_history(ticker)
            if hist is None or len(hist) < 1:
                print(f"  ⚠️ 指数 {meta['name']} 无数据")
                continue

            prices = hist["Close"].tolist()
            price = float(prices[-1])
            prev_close = float(prices[-2]) if len(prices) >= 2 else price
            if prev_close == 0:
                prev_close = price

            change_amt = price - prev_close if prev_close > 0 else 0
            change_pct = (change_amt / prev_close * 100) if prev_close > 0 else 0

            # 获取成交量
            try:
                volume = hist["Volume"].iloc[-1]
                amount = price * float(volume)
            except Exception:
                amount = 0

            results.append({
                "name": meta["name"],
                "code": meta["code"],
                "price": round(price, 2),
                "change_pct": round(change_pct, 2),
                "change_amt": round(change_amt, 2),
                "amount": round(amount, 2),
            })
            print(f"  ✅ 指数 {meta['name']}: {price:.2f} ({change_pct:+.2f}%)")
            time.sleep(1.5)  # 请求间隔

        except Exception as e:
            print(f"  ❌ 指数 {meta['name']}: {str(e)[:80]}")

    return results


# ============ 个股行情 ============

STOCK_MAP = {
    "600519.SS": "贵州茅台",
    "000858.SZ": "五粮液",
    "601318.SS": "中国平安",
    "000001.SZ": "平安银行",
    "300750.SZ": "宁德时代",
    "002594.SZ": "比亚迪",
    "600036.SS": "招商银行",
    "601899.SS": "紫金矿业",
}


def fetch_stock_yahoo() -> List[Dict]:
    """通过 yfinance 获取个股行情"""
    results = []
    for ticker, name in STOCK_MAP.items():
        try:
            hist = _yf_history(ticker)
            if hist is None or len(hist) < 1:
                print(f"  ⚠️ 个股 {name} 无数据")
                continue

            prices = hist["Close"].tolist()
            price = float(prices[-1])
            prev_close = float(prices[-2]) if len(prices) >= 2 else price
            if prev_close == 0:
                prev_close = price

            change_amt = price - prev_close if prev_close > 0 else 0
            change_pct = (change_amt / prev_close * 100) if prev_close > 0 else 0

            # 获取成交量
            try:
                volume = hist["Volume"].iloc[-1]
                amount = price * float(volume)
            except Exception:
                amount = 0

            results.append({
                "name": name,
                "code": ticker.split(".")[0],
                "price": round(price, 2),
                "change_pct": round(change_pct, 2),
                "change_amt": round(change_amt, 2),
                "amount": round(amount, 2),
                "turnover_rate": 0.0,
                "pe": 0.0,
                "pb": 0.0,
                "high": round(price, 2),
                "low": round(price, 2),
                "open": round(price, 2),
                "prev_close": round(prev_close, 2),
            })
            print(f"  ✅ 个股 {name}: {price:.2f} ({change_pct:+.2f}%)")
            time.sleep(1.5)  # 请求间隔

        except Exception as e:
            print(f"  ❌ 个股 {name}: {str(e)[:80]}")

    return results


# ============ 市场概况（从指数推导） ============

def fetch_market_overview_yahoo() -> Dict[str, Any]:
    """估算市场概况"""
    try:
        indices = fetch_index_yahoo()
        up = sum(1 for i in indices if i.get("change_pct", 0) > 0)
        down = sum(1 for i in indices if i.get("change_pct", 0) < 0)
        total_stocks = 5037

        if up > down:
            total_up = int(total_stocks * 0.55)
            total_down = int(total_stocks * 0.40)
        elif down > up:
            total_up = int(total_stocks * 0.40)
            total_down = int(total_stocks * 0.55)
        else:
            total_up = int(total_stocks * 0.45)
            total_down = int(total_stocks * 0.45)

        total_flat = total_stocks - total_up - total_down

        overview = {
            "total_up": total_up,
            "total_down": total_down,
            "total_flat": total_flat,
            "limit_up": 0,
            "limit_down": 0,
            "total_stocks": total_stocks,
        }
        print(f"  ✅ 市场概况: 上涨 {total_up} / 下跌 {total_down}")
        return overview

    except Exception as e:
        print(f"  ⚠️ 市场概况: {str(e)[:80]}")
        return {
            "total_up": 0, "total_down": 0, "total_flat": 0,
            "limit_up": 0, "limit_down": 0, "total_stocks": 0,
        }


# ============ 板块/北向（yfinance 不支持） ============

def fetch_sector_yahoo() -> List[Dict]:
    print("  ℹ️ 板块排名: yfinance 暂不支持")
    return []


def fetch_north_flow_yahoo() -> List[Dict]:
    print("  ℹ️ 北向资金: yfinance 暂不支持")
    return []


# ============ 主入口 ============

def fetch_all(watchlist_path: str) -> Dict[str, Any]:
    print("=" * 50)
    print("📊 股市数据抓取启动（yfinance / Yahoo Finance）")

    data = {}

    print("📈 抓取市场概况...")
    data["overview"] = fetch_market_overview_yahoo()

    print("📊 抓取指数行情...")
    data["indices"] = fetch_index_yahoo()
    print(f"   → {len(data['indices'])} 条指数")

    print("🔍 抓取个股行情...")
    data["stocks"] = fetch_stock_yahoo()
    print(f"   → {len(data['stocks'])} 只个股")

    print("🏭 抓取板块排名...")
    data["sectors"] = fetch_sector_yahoo()

    print("💰 抓取北向资金...")
    data["north_flow"] = fetch_north_flow_yahoo()

    beijing_tz = timezone(timedelta(hours=8))
    data["generated_at"] = datetime.now(beijing_tz).strftime("%Y-%m-%d %H:%M:%S")
    data["generated_at_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    print(f"✅ 完成 @ {data['generated_at']}")
    print("=" * 50)
    return data


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    wl_path = os.path.join(base_dir, "data", "watchlist.json")
    data = fetch_all(wl_path)
    print(json.dumps(data, ensure_ascii=False, indent=2, default=str))
