"""测试分析增强版报告生成"""
import sys, json, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from report import generate_stock_html, save_report

# 读取 watchlist 配置
watchlist_path = os.path.join(os.path.dirname(__file__), 'data', 'watchlist.json')
with open(watchlist_path, 'r', encoding='utf-8') as f:
    watchlist_config = json.load(f)

mock_data = {
    "overview": {"total_up": 2847, "total_down": 1956, "total_flat": 234, "limit_up": 42, "limit_down": 8, "total_stocks": 5037},
    "indices": [
        {"name": "上证指数", "code": "000001", "price": 3356.72, "change_pct": 0.85, "change_amt": 28.31, "amount": 452300000000, "ma5": 3338.50, "ma3": 3348.20, "above_ma5": True, "above_ma3": True, "history_5d": [3312.0, 3325.8, 3340.2, 3348.5, 3356.72]},
        {"name": "深证成指", "code": "399001", "price": 10892.45, "change_pct": 1.23, "change_amt": 132.67, "amount": 583100000000, "ma5": 10780.0, "ma3": 10820.0, "above_ma5": True, "above_ma3": True, "history_5d": [10680.0, 10750.0, 10810.0, 10840.0, 10892.45]},
        {"name": "创业板指", "code": "399006", "price": 2156.33, "change_pct": 1.67, "change_amt": 35.41, "amount": 267800000000, "ma5": 2130.0, "ma3": 2142.0, "above_ma5": True, "above_ma3": True, "history_5d": [2110.0, 2125.0, 2138.0, 2148.0, 2156.33]},
        {"name": "科创50", "code": "000688", "price": 986.51, "change_pct": -0.32, "change_amt": -3.17, "amount": 54320000000, "ma5": 990.0, "ma3": 988.5, "above_ma5": False, "above_ma3": False, "history_5d": [995.0, 992.0, 990.0, 988.0, 986.51]},
        {"name": "沪深300", "code": "000300", "price": 3921.88, "change_pct": 0.56, "change_amt": 21.84, "amount": 278600000000, "ma5": 3905.0, "ma3": 3912.0, "above_ma5": True, "above_ma3": True, "history_5d": [3880.0, 3895.0, 3905.0, 3912.0, 3921.88]},
        {"name": "上证50", "code": "000016", "price": 2654.12, "change_pct": 0.21, "change_amt": 5.56, "amount": 156700000000, "ma5": 2648.0, "ma3": 2650.0, "above_ma5": True, "above_ma3": True, "history_5d": [2640.0, 2645.0, 2650.0, 2652.0, 2654.12]},
    ],
    "stocks": [
        {"name": "贵州茅台", "code": "600519", "price": 1568.00, "change_pct": 1.25, "change_amt": 19.35, "amount": 89230000000, "turnover_rate": 0.71, "pe": 28.5, "pb": 9.8, "high": 1572.50, "low": 1550.00, "open": 1552.00, "prev_close": 1548.65, "ma5": 1550.0, "ma10": 1542.0, "ma20": 1535.0, "rsi": 62.3, "macd": 5.23, "macd_signal": 3.81, "macd_hist": 1.42, "k": 68.2, "d": 58.5, "j": 87.6, "bb_upper": 1585.0, "bb_middle": 1535.0, "bb_lower": 1485.0, "bb_position": 66.0, "vol_ratio": 1.2, "amplitude": 1.45, "score": 73, "signal": "偏多", "signal_color": "red", "history_5d": [1530.0, 1540.0, 1545.0, 1550.0, 1568.0], "history_20d": [1510.0, 1515.0, 1520.0, 1525.0, 1530.0, 1535.0, 1528.0, 1532.0, 1538.0, 1540.0, 1535.0, 1542.0, 1545.0, 1548.0, 1550.0, 1545.0, 1552.0, 1555.0, 1558.0, 1568.0]},
        {"name": "五粮液", "code": "000858", "price": 142.35, "change_pct": -0.42, "change_amt": -0.60, "amount": 34560000000, "turnover_rate": 0.89, "pe": 18.3, "pb": 5.2, "high": 144.20, "low": 141.50, "open": 143.80, "prev_close": 142.95, "ma5": 143.5, "ma10": 144.0, "ma20": 145.0, "rsi": 45.0, "macd": -1.23, "macd_signal": -0.85, "macd_hist": -0.38, "k": 42.5, "d": 48.2, "j": 31.1, "bb_upper": 150.0, "bb_middle": 145.0, "bb_lower": 140.0, "bb_position": 47.0, "vol_ratio": 0.8, "amplitude": 1.90, "score": 42, "signal": "中性", "signal_color": "gray", "history_5d": [145.0, 144.5, 143.8, 143.2, 142.35], "history_20d": [148.0, 147.5, 147.0, 146.5, 146.0, 145.8, 145.5, 145.0, 144.8, 144.5, 144.0, 143.5, 143.8, 144.2, 143.5, 143.0, 142.8, 142.5, 142.8, 142.35]},
        {"name": "中国平安", "code": "601318", "price": 52.36, "change_pct": 0.77, "change_amt": 0.40, "amount": 23450000000, "turnover_rate": 0.45, "pe": 9.1, "pb": 1.2, "high": 52.80, "low": 51.90, "open": 52.00, "prev_close": 51.96, "ma5": 51.8, "ma10": 51.5, "ma20": 51.0, "rsi": 58.0, "macd": 0.35, "macd_signal": 0.22, "macd_hist": 0.13, "k": 55.0, "d": 52.3, "j": 60.4, "bb_upper": 54.0, "bb_middle": 51.0, "bb_lower": 48.0, "bb_position": 55.3, "vol_ratio": 1.0, "amplitude": 1.73, "score": 65, "signal": "偏多", "signal_color": "red", "history_5d": [51.0, 51.3, 51.5, 51.8, 52.36], "history_20d": [49.5, 49.8, 50.0, 50.2, 50.5, 50.8, 51.0, 50.7, 50.5, 50.8, 51.0, 51.2, 51.0, 51.3, 51.5, 51.2, 51.5, 51.8, 52.0, 52.36]},
        {"name": "平安银行", "code": "000001", "price": 12.85, "change_pct": 1.18, "change_amt": 0.15, "amount": 8765000000, "turnover_rate": 0.55, "pe": 5.6, "pb": 0.7, "high": 12.92, "low": 12.68, "open": 12.70, "prev_close": 12.70, "ma5": 12.6, "ma10": 12.5, "ma20": 12.3, "rsi": 60.0, "macd": 0.08, "macd_signal": 0.05, "macd_hist": 0.03, "k": 58.0, "d": 54.0, "j": 66.0, "bb_upper": 13.2, "bb_middle": 12.3, "bb_lower": 11.4, "bb_position": 72.7, "vol_ratio": 1.1, "amplitude": 1.89, "score": 68, "signal": "偏多", "signal_color": "red", "history_5d": [12.3, 12.4, 12.5, 12.6, 12.85], "history_20d": [12.0, 12.05, 12.1, 12.15, 12.2, 12.25, 12.3, 12.28, 12.25, 12.3, 12.35, 12.4, 12.38, 12.42, 12.45, 12.5, 12.48, 12.55, 12.65, 12.85]},
        {"name": "宁德时代", "code": "300750", "price": 218.50, "change_pct": 2.33, "change_amt": 4.99, "amount": 56780000000, "turnover_rate": 1.23, "pe": 22.1, "pb": 6.3, "high": 220.00, "low": 213.50, "open": 214.00, "prev_close": 213.51, "ma5": 212.0, "ma10": 208.0, "ma20": 205.0, "rsi": 72.0, "macd": 3.85, "macd_signal": 2.50, "macd_hist": 1.35, "k": 72.0, "d": 62.0, "j": 92.0, "bb_upper": 225.0, "bb_middle": 205.0, "bb_lower": 185.0, "bb_position": 67.5, "vol_ratio": 1.6, "amplitude": 3.04, "score": 70, "signal": "偏多", "signal_color": "red", "history_5d": [208.0, 210.0, 212.0, 214.0, 218.50], "history_20d": [195.0, 196.0, 198.0, 200.0, 199.0, 201.0, 203.0, 202.0, 204.0, 205.0, 206.0, 207.0, 208.0, 206.0, 207.0, 209.0, 210.0, 212.0, 215.0, 218.50]},
        {"name": "比亚迪", "code": "002594", "price": 285.60, "change_pct": -1.05, "change_amt": -3.03, "amount": 67890000000, "turnover_rate": 1.56, "pe": 25.8, "pb": 5.9, "high": 290.20, "low": 284.30, "open": 289.00, "prev_close": 288.63, "ma5": 290.0, "ma10": 292.0, "ma20": 288.0, "rsi": 38.0, "macd": -2.15, "macd_signal": -1.50, "macd_hist": -0.65, "k": 35.0, "d": 42.0, "j": 21.0, "bb_upper": 298.0, "bb_middle": 288.0, "bb_lower": 278.0, "bb_position": 76.0, "vol_ratio": 0.9, "amplitude": 2.06, "score": 30, "signal": "弱势卖出", "signal_color": "green", "history_5d": [295.0, 293.0, 291.0, 289.0, 285.60], "history_20d": [285.0, 286.0, 288.0, 290.0, 292.0, 294.0, 295.0, 293.0, 291.0, 290.0, 292.0, 293.0, 294.0, 292.0, 290.0, 291.0, 293.0, 290.0, 288.0, 285.60]},
        {"name": "招商银行", "code": "600036", "price": 38.72, "change_pct": 0.52, "change_amt": 0.20, "amount": 18920000000, "turnover_rate": 0.38, "pe": 7.8, "pb": 1.1, "high": 38.90, "low": 38.45, "open": 38.50, "prev_close": 38.52, "ma5": 38.3, "ma10": 38.0, "ma20": 37.5, "rsi": 56.0, "macd": 0.22, "macd_signal": 0.15, "macd_hist": 0.07, "k": 56.0, "d": 52.0, "j": 64.0, "bb_upper": 39.5, "bb_middle": 37.5, "bb_lower": 35.5, "bb_position": 60.5, "vol_ratio": 1.0, "amplitude": 1.17, "score": 63, "signal": "偏多", "signal_color": "red", "history_5d": [37.8, 38.0, 38.1, 38.3, 38.72], "history_20d": [36.5, 36.8, 37.0, 37.2, 37.4, 37.5, 37.3, 37.4, 37.6, 37.8, 37.5, 37.8, 38.0, 37.9, 38.1, 38.0, 38.2, 38.3, 38.5, 38.72]},
        {"name": "紫金矿业", "code": "601899", "price": 18.93, "change_pct": 3.15, "change_amt": 0.58, "amount": 45670000000, "turnover_rate": 2.01, "pe": 15.2, "pb": 4.1, "high": 19.10, "low": 18.30, "open": 18.35, "prev_close": 18.35, "ma5": 18.0, "ma10": 17.5, "ma20": 17.0, "rsi": 78.0, "macd": 0.65, "macd_signal": 0.40, "macd_hist": 0.25, "k": 82.0, "d": 70.0, "j": 106.0, "bb_upper": 19.5, "bb_middle": 17.0, "bb_lower": 14.5, "bb_position": 79.1, "vol_ratio": 2.0, "amplitude": 4.36, "score": 75, "signal": "强烈买入", "signal_color": "red", "history_5d": [17.2, 17.5, 17.8, 18.2, 18.93], "history_20d": [15.5, 15.8, 16.0, 16.2, 16.5, 16.8, 17.0, 16.8, 17.0, 17.2, 17.0, 17.2, 17.5, 17.3, 17.5, 17.8, 17.6, 17.8, 18.0, 18.93]},
    ],
    "sectors": [
        {"name": "创业板ETF", "code": "159915", "change_pct": 2.15, "type": "指数ETF"},
        {"name": "半导体ETF", "code": "512480", "change_pct": 1.89, "type": "行业ETF"},
        {"name": "黄金ETF", "code": "159934", "change_pct": 1.56, "type": "商品ETF"},
        {"name": "沪深300ETF", "code": "510300", "change_pct": 0.78, "type": "指数ETF"},
        {"name": "新能源车ETF", "code": "515030", "change_pct": 0.45, "type": "行业ETF"},
        {"name": "中证500ETF", "code": "510500", "change_pct": 0.32, "type": "指数ETF"},
        {"name": "上证50ETF", "code": "510050", "change_pct": 0.18, "type": "指数ETF"},
        {"name": "医药ETF", "code": "512010", "change_pct": -0.23, "type": "行业ETF"},
        {"name": "证券ETF", "code": "512880", "change_pct": -0.56, "type": "行业ETF"},
        {"name": "军工ETF", "code": "512660", "change_pct": -0.78, "type": "行业ETF"},
    ],
    "north_flow": [
        {"date": "2026-06-02", "net_buy": 86.52},
        {"date": "2026-06-01", "net_buy": -32.18},
        {"date": "2026-05-31", "net_buy": 125.67},
        {"date": "2026-05-30", "net_buy": 45.33},
        {"date": "2026-05-29", "net_buy": -18.90},
    ],
    "generated_at": "2026-06-02 18:46:00",
    "generated_at_utc": "2026-06-02T10:46:00Z",
    "watchlist_config": watchlist_config,
}

html = generate_stock_html(mock_data)
save_report(html, "docs/index.html")
print("Done")
