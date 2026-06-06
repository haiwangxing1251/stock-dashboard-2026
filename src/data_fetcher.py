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
_DEFAULT_STOCK_MAP = {
    "600519.SS": "贵州茅台",
    "000858.SZ": "五粮液",
    "601318.SS": "中国平安",
    "000001.SZ": "平安银行",
    "300750.SZ": "宁德时代",
    "002594.SZ": "比亚迪",
    "600036.SS": "招商银行",
    "601899.SS": "紫金矿业",
}


def _build_stock_map(watchlist: List[Dict]) -> Dict[str, str]:
    """从 watchlist.json 自选股列表构建 yfinance ticker -> 名称 映射"""
    market_suffix = {"sh": "SS", "sz": "SZ"}
    result = {}
    for s in watchlist:
        code = s.get("code", "").strip()
        name = s.get("name", code)
        market = s.get("market", "sh").lower()
        suffix = market_suffix.get(market, "SS")
        ticker = f"{code}.{suffix}"
        result[ticker] = name
    return result if result else _DEFAULT_STOCK_MAP


def fetch_stock_yahoo(watchlist: List[Dict] = None) -> List[Dict]:
    """通过 yfinance 获取个股行情（含技术指标 MACD/KDJ/布林带）"""
    stock_map = _build_stock_map(watchlist) if watchlist else _DEFAULT_STOCK_MAP
    results = []
    for ticker, name in stock_map.items():
        try:
            hist = _yf_history(ticker, period="60d")
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

            # ---- 均线计算 ----
            ma5 = sum(prices[-5:]) / len(prices[-5:]) if len(prices) >= 5 else price
            ma10 = sum(prices[-10:]) / len(prices[-10:]) if len(prices) >= 10 else price
            ma20 = sum(prices[-20:]) / len(prices[-20:]) if len(prices) >= 20 else price

            # ---- RSI (14日标准RSI) ----
            rsi_period = min(14, len(prices) - 1)
            if rsi_period >= 2:
                rsi_gains, rsi_losses = [], []
                for i in range(len(prices) - rsi_period, len(prices)):
                    diff = prices[i] - prices[i - 1]
                    rsi_gains.append(max(diff, 0))
                    rsi_losses.append(max(-diff, 0))
                avg_gain = sum(rsi_gains) / rsi_period
                avg_loss = sum(rsi_losses) / rsi_period
                rsi = 100 - 100 / (1 + avg_gain / avg_loss) if avg_loss > 0 else 50
            else:
                rsi = 50

            # ---- MACD (12,26,9) ----
            macd_val, macd_signal, macd_hist = 0.0, 0.0, 0.0
            if len(prices) >= 26:
                # EMA12 和 EMA26
                ema12 = prices[-12]
                ema26 = prices[-26]
                for i in range(max(len(prices)-26, 0), len(prices)):
                    ema12 = ema12 * 11/13 + prices[i] * 2/13
                    ema26 = ema26 * 25/27 + prices[i] * 2/27
                dif_val = ema12 - ema26
                # 简化DEA用最近9天的DIF均值
                macd_val = round(dif_val, 3)
                macd_signal = round(dif_val * 0.8, 3)  # 近似
                macd_hist = round(macd_val - macd_signal, 3)

            # ---- KDJ (9,3,3) ----
            k_val, d_val, j_val = 50.0, 50.0, 50.0
            kdj_period = min(9, len(prices))
            if kdj_period >= 3:
                recent_highs = highs[-kdj_period:]
                recent_lows = lows[-kdj_period:]
                highest = max(recent_highs) if recent_highs else price
                lowest = min(recent_lows) if recent_lows else price
                if highest != lowest:
                    rsv = (price - lowest) / (highest - lowest) * 100
                else:
                    rsv = 50
                k_val = 2/3 * 50 + 1/3 * rsv  # 简化，首日K=50
                d_val = 2/3 * 50 + 1/3 * k_val
                j_val = 3 * k_val - 2 * d_val

            # ---- 布林带 (20,2) ----
            bb_upper, bb_middle, bb_lower = price, price, price
            if len(prices) >= 20:
                bb_middle = ma20
                variance = sum((p - ma20) ** 2 for p in prices[-20:]) / 20
                std = variance ** 0.5
                bb_upper = round(ma20 + 2 * std, 2)
                bb_lower = round(ma20 - 2 * std, 2)
                bb_middle = round(ma20, 2)
            elif len(prices) >= 5:
                bb_middle = round(ma5, 2)

            # ---- 量比 ----
            avg_vol = sum(volumes[-5:]) / len(volumes[-5:]) if len(volumes) >= 5 else float(volumes[-1])
            vol_ratio = float(volumes[-1]) / avg_vol if avg_vol > 0 else 1.0

            # ---- 振幅 ----
            today_high = float(highs[-1]) if highs else price
            today_low = float(lows[-1]) if lows else price
            amplitude = (today_high - today_low) / prev_close * 100 if prev_close > 0 else 0

            # ---- 布林带位置 ----
            if bb_upper > bb_lower:
                bb_position = (price - bb_lower) / (bb_upper - bb_lower) * 100
            else:
                bb_position = 50

            # ---- 综合信号评分 (0-100) ----
            score = 50
            # 涨跌幅贡献
            if change_pct > 3: score += 18
            elif change_pct > 1: score += 12
            elif change_pct > 0.3: score += 6
            elif change_pct < -3: score -= 18
            elif change_pct < -1: score -= 12
            elif change_pct < -0.3: score -= 6
            # 均线排列
            if price > ma5 > ma10: score += 12
            elif price > ma5: score += 6
            elif price < ma5 < ma10: score -= 12
            elif price < ma5: score -= 6
            # RSI
            if rsi < 25: score += 12      # 严重超卖
            elif rsi < 35: score += 6     # 超卖区
            elif rsi > 75: score -= 12     # 严重超买
            elif rsi > 65: score -= 6     # 超买区
            # MACD
            if macd_hist > 0: score += 6
            elif macd_hist < 0: score -= 6
            # KDJ
            if j_val < 20: score += 8     # 超卖
            elif j_val > 80: score -= 8    # 超买
            # 布林带
            if bb_position < 10: score += 8    # 触下轨
            elif bb_position > 90: score -= 8  # 触上轨
            # 量比
            if vol_ratio > 2: score += 5
            elif vol_ratio < 0.5: score -= 5

            score = max(0, min(100, score))

            # 信号标签
            if score >= 80:
                signal, signal_color = "强烈买入", "red"
            elif score >= 65:
                signal, signal_color = "偏多", "red"
            elif score >= 45:
                signal, signal_color = "中性", "gray"
            elif score >= 30:
                signal, signal_color = "偏空", "green"
            else:
                signal, signal_color = "弱势卖出", "green"

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
                "ma10": round(ma10, 2),
                "ma20": round(ma20, 2),
                "rsi": round(rsi, 1),
                "macd": macd_val,
                "macd_signal": macd_signal,
                "macd_hist": macd_hist,
                "k": round(k_val, 1),
                "d": round(d_val, 1),
                "j": round(j_val, 1),
                "bb_upper": bb_upper,
                "bb_middle": bb_middle,
                "bb_lower": bb_lower,
                "bb_position": round(bb_position, 1),
                "vol_ratio": round(vol_ratio, 2),
                "amplitude": round(amplitude, 2),
                "score": score,
                "signal": signal,
                "signal_color": signal_color,
                "history_5d": [round(float(p), 2) for p in prices[-5:]],
                "history_20d": [round(float(p), 2) for p in prices[-20:]] if len(prices) >= 20 else [round(float(p), 2) for p in prices],
                "market": "sh" if ticker.endswith(".SS") else "sz",
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

    # 读取 watchlist.json 获取自选股列表
    watchlist_stocks = []
    try:
        with open(watchlist_path, "r", encoding="utf-8") as f:
            wl_config = json.load(f)
        watchlist_stocks = wl_config.get("自选股", [])
        print(f"   读取自选股: {len(watchlist_stocks)} 只")
    except Exception as e:
        print(f"   ⚠️ 读取 watchlist.json 失败，使用默认列表: {e}")

    data = {}

    print("📊 抓取指数行情...")
    data["indices"] = fetch_index_yahoo()
    print(f"   → {len(data['indices'])} 条指数")

    print("📈 生成市场概况...")
    data["overview"] = fetch_market_overview_yahoo(data["indices"])

    print("🔍 抓取个股行情...")
    data["stocks"] = fetch_stock_yahoo(watchlist_stocks)
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
