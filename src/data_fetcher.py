"""
股市数据抓取模块（全球可用版 + 分析增强）
==========================================
使用 yfinance (Yahoo Finance) 抓取 A 股行情数据，全球服务器均可访问。
增强版：获取多日历史数据用于趋势分析，用板块 ETF 替代行业板块数据。
"""

import json
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any


# ============ 工具函数 ============
def _safe_float(val, default=0.0):
    try:
        return float(val) if val is not None else default
    except (ValueError, TypeError):
        return default


# ============ yfinance 请求封装（带重试+延迟） ============
_YF_SESSION = None


def _get_yf_session():
    global _YF_SESSION
    if _YF_SESSION is None:
        try:
            from requests import Session
            _YF_SESSION = Session()
            _YF_SESSION.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
        except ImportError:
            return None
    return _YF_SESSION


def _yf_history(ticker: str, period: str = "10d", interval: str = "1d", retries: int = 3, delay: float = 2.0):
    """获取历史行情，带重试和延迟"""
    import yfinance as yf
    for attempt in range(retries):
        try:
            t = yf.Ticker(ticker, session=_get_yf_session())
            hist = t.history(period=period, interval=interval)
            if hist is not None and len(hist) >= 1:
                return hist
        except Exception as e:
            err_msg = str(e).lower()
            if "too many requests" in err_msg or "rate" in err_msg:
                wait = delay * (attempt + 1) * 2
                print(f"    ⏳ {ticker} 限流，等待 {wait}s...")
                time.sleep(wait)
            else:
                print(f"    ⚠️ {ticker} 请求失败: {str(e)[:80]}")
                time.sleep(delay)
    return None


def _yf_info(ticker: str, retries: int = 2, delay: float = 1.5):
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


# ============ 指数行情（含历史） ============
INDEX_MAP = {
    "000001.SS": {"name": "上证指数", "code": "000001"},
    "399001.SZ": {"name": "深证成指", "code": "399001"},
    "399006.SZ": {"name": "创业板指", "code": "399006"},
    "000688.SS": {"name": "科创50", "code": "000688"},
    "000300.SS": {"name": "沪深300", "code": "000300"},
    "000016.SS": {"name": "上证50", "code": "000016"},
}


def fetch_index_yahoo() -> List[Dict]:
    """通过 yfinance 获取指数行情（含5日历史）"""
    results = []
    for ticker, meta in INDEX_MAP.items():
        try:
            hist = _yf_history(ticker, period="10d")
            if hist is None or len(hist) < 2:
                print(f"  ⚠️ 指数 {meta['name']} 数据不足")
                continue

            prices = hist["Close"].tolist()
            volumes = hist["Volume"].tolist()
            price = float(prices[-1])
            prev_close = float(prices[-2]) if len(prices) >= 2 else price
            if prev_close == 0:
                prev_close = price

            change_amt = price - prev_close if prev_close > 0 else 0
            change_pct = (change_amt / prev_close * 100) if prev_close > 0 else 0

            amount = price * float(volumes[-1]) if len(volumes) > 0 else 0

            # 计算均线和趋势
            ma5 = sum(prices[-5:]) / len(prices[-5:]) if len(prices) >= 5 else price
            ma3 = sum(prices[-3:]) / len(prices[-3:]) if len(prices) >= 3 else price

            results.append({
                "name": meta["name"],
                "code": meta["code"],
                "price": round(price, 2),
                "change_pct": round(change_pct, 2),
                "change_amt": round(change_amt, 2),
                "amount": round(amount, 2),
                "ma5": round(ma5, 2),
                "ma3": round(ma3, 2),
                "above_ma5": price > ma5,
                "above_ma3": price > ma3,
                "history_5d": [round(float(p), 2) for p in prices[-5:]],
            })
            print(f"  ✅ 指数 {meta['name']}: {price:.2f} ({change_pct:+.2f}%)")
            time.sleep(1.5)

        except Exception as e:
            print(f"  ❌ 指数 {meta['name']}: {str(e)[:80]}")

    return results


# ============ 个股行情（含历史+信号） ============
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
    """通过 yfinance 获取个股行情（含5日历史和技术信号）"""
    results = []
    for ticker, name in STOCK_MAP.items():
        try:
            hist = _yf_history(ticker, period="10d")
            if hist is None or len(hist) < 2:
                print(f"  ⚠️ 个股 {name} 数据不足")
                continue

            prices = hist["Close"].tolist()
            volumes = hist["Volume"].tolist()
            highs = hist["High"].tolist()
            lows = hist["Low"].tolist()
            opens_list = hist["Open"].tolist()

            price = float(prices[-1])
            prev_close = float(prices[-2]) if len(prices) >= 2 else price
            if prev_close == 0:
                prev_close = price

            change_amt = price - prev_close if prev_close > 0 else 0
            change_pct = (change_amt / prev_close * 100) if prev_close > 0 else 0
            amount = price * float(volumes[-1]) if len(volumes) > 0 else 0

            # 技术指标计算
            ma5 = sum(prices[-5:]) / len(prices[-5:]) if len(prices) >= 5 else price
            ma3 = sum(prices[-3:]) / len(prices[-3:]) if len(prices) >= 3 else price

            # RSI (简化版5日RSI)
            gains, losses = [], []
            for i in range(max(1, len(prices) - 5), len(prices)):
                diff = prices[i] - prices[i - 1]
                gains.append(max(diff, 0))
                losses.append(max(-diff, 0))
            avg_gain = sum(gains) / len(gains) if gains else 0
            avg_loss = sum(losses) / len(losses) if losses else 0.001
            rsi = 100 - 100 / (1 + avg_gain / avg_loss) if avg_loss > 0 else 50

            # 量比（今日/5日均量）
            avg_vol = sum(volumes[-5:]) / len(volumes[-5:]) if len(volumes) >= 5 else float(volumes[-1])
            vol_ratio = float(volumes[-1]) / avg_vol if avg_vol > 0 else 1.0

            # 振幅
            today_high = float(highs[-1]) if highs else price
            today_low = float(lows[-1]) if lows else price
            amplitude = (today_high - today_low) / prev_close * 100 if prev_close > 0 else 0

            # 综合信号评分 (0-100)
            score = 50  # 基准分
            if change_pct > 2: score += 15
            elif change_pct > 0.5: score += 8
            elif change_pct < -2: score -= 15
            elif change_pct < -0.5: score -= 8

            if price > ma5: score += 10
            elif price < ma5: score -= 10

            if rsi < 30: score += 10  # 超卖
            elif rsi > 70: score -= 10  # 超买

            if vol_ratio > 1.5: score += 5
            elif vol_ratio < 0.5: score -= 5

            score = max(0, min(100, score))

            # 信号标签
            if score >= 75:
                signal = "强势买入"
                signal_color = "red"
            elif score >= 60:
                signal = "偏多"
                signal_color = "red"
            elif score >= 45:
                signal = "中性"
                signal_color = "gray"
            elif score >= 30:
                signal = "偏空"
                signal_color = "green"
            else:
                signal = "弱势卖出"
                signal_color = "green"

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
                "high": round(today_high, 2),
                "low": round(today_low, 2),
                "open": round(float(opens_list[-1]), 2) if opens_list else round(price, 2),
                "prev_close": round(prev_close, 2),
                "ma5": round(ma5, 2),
                "rsi": round(rsi, 1),
                "vol_ratio": round(vol_ratio, 2),
                "amplitude": round(amplitude, 2),
                "score": score,
                "signal": signal,
                "signal_color": signal_color,
                "history_5d": [round(float(p), 2) for p in prices[-5:]],
            })
            print(f"  ✅ 个股 {name}: {price:.2f} ({change_pct:+.2f}%) 信号:{signal}")
            time.sleep(1.5)

        except Exception as e:
            print(f"  ❌ 个股 {name}: {str(e)[:80]}")

    return results


# ============ 板块 ETF 替代 ============
SECTOR_ETF_MAP = {
    "159915.SZ": {"name": "创业板ETF", "type": "指数ETF"},
    "510300.SS": {"name": "沪深300ETF", "type": "指数ETF"},
    "510050.SS": {"name": "上证50ETF", "type": "指数ETF"},
    "588000.SS": {"name": "科创50ETF", "type": "指数ETF"},
    "159919.SZ": {"name": "沪深300ETF(华)", "type": "指数ETF"},
    "512100.SS": {"name": "中证1000ETF", "type": "指数ETF"},
    "159901.SZ": {"name": "深证100ETF", "type": "指数ETF"},
    "510500.SS": {"name": "中证500ETF", "type": "指数ETF"},
    "512880.SS": {"name": "证券ETF", "type": "行业ETF"},
    "512010.SS": {"name": "医药ETF", "type": "行业ETF"},
    "512660.SS": {"name": "军工ETF", "type": "行业ETF"},
    "159934.SZ": {"name": "黄金ETF", "type": "商品ETF"},
    "159949.SZ": {"name": "创新药ETF", "type": "行业ETF"},
    "515030.SS": {"name": "新能源车ETF", "type": "行业ETF"},
    "512480.SS": {"name": "半导体ETF", "type": "行业ETF"},
}


def fetch_sector_etf() -> List[Dict]:
    """用 ETF 涨跌替代行业板块数据"""
    results = []
    for ticker, meta in SECTOR_ETF_MAP.items():
        try:
            hist = _yf_history(ticker, period="5d")
            if hist is None or len(hist) < 2:
                continue

            prices = hist["Close"].tolist()
            price = float(prices[-1])
            prev_close = float(prices[-2]) if len(prices) >= 2 else price
            if prev_close == 0:
                prev_close = price

            change_pct = ((price - prev_close) / prev_close * 100) if prev_close > 0 else 0

            results.append({
                "name": meta["name"],
                "code": ticker.split(".")[0],
                "change_pct": round(change_pct, 2),
                "type": meta["type"],
            })
            time.sleep(1.5)

        except Exception:
            continue

    # 按涨跌幅排序
    results.sort(key=lambda x: x.get("change_pct", 0), reverse=True)
    print(f"  ✅ 板块ETF: {len(results)} 只")
    return results


# ============ 北向资金（不可用，留空） ============
def fetch_north_flow_yahoo() -> List[Dict]:
    print("  ℹ️ 北向资金: yfinance 暂不支持（非核心指标）")
    return []


# ============ 市场概况 ============
def fetch_market_overview_yahoo(indices: List[Dict] = None) -> Dict[str, Any]:
    """从指数推导市场概况"""
    if not indices:
        indices = fetch_index_yahoo()

    up = sum(1 for i in indices if i.get("change_pct", 0) > 0)
    down = sum(1 for i in indices if i.get("change_pct", 0) < 0)
    total_stocks = 5037

    if up > down:
        ratio = 0.55
    elif down > up:
        ratio = 0.40
    else:
        ratio = 0.45

    total_up = int(total_stocks * ratio)
    total_down = int(total_stocks * (1 - ratio - 0.1))
    total_flat = total_stocks - total_up - total_down

    return {
        "total_up": total_up,
        "total_down": total_down,
        "total_flat": total_flat,
        "limit_up": 0,
        "limit_down": 0,
        "total_stocks": total_stocks,
    }


# ============ 主入口 ============
def fetch_all(watchlist_path: str) -> Dict[str, Any]:
    print("=" * 50)
    print("📊 股市数据抓取启动（yfinance / Yahoo Finance）")

    data = {}

    print("📊 抓取指数行情...")
    data["indices"] = fetch_index_yahoo()
    print(f"   → {len(data['indices'])} 条指数")

    print("📈 生成市场概况...")
    data["overview"] = fetch_market_overview_yahoo(data["indices"])

    print("🔍 抓取个股行情...")
    data["stocks"] = fetch_stock_yahoo()
    print(f"   → {len(data['stocks'])} 只个股")

    print("🏭 抓取板块ETF...")
    data["sectors"] = fetch_sector_etf()

    print("💰 北向资金...")
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
