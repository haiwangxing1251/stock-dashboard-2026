"""
股市仪表盘 — 自包含 HTML 报告生成器（分析增强版）
==================================================
生成美观的中文股市仪表盘，纯 CSS/JS，无外部依赖。

模块:
- 市场总览（涨跌家数、涨停跌停）
- 主要指数行情（含趋势分析）
- 自选股行情（含技术信号、RSI、量比）
- 板块 ETF 涨跌排名（替代行业板块）
- 北向资金流向
- 🆕 市场情绪分析
- 🆕 指数趋势图（纯 CSS/JS 折线图）
- 🆕 个股信号雷达
- 🆕 综合分析总结
"""

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List


# ============================================================
# 配色方案（中国股市红涨绿跌）
# ============================================================
COLORS = {
    'bg':            '#0f1117',
    'card_bg':       '#1a1d29',
    'card_border':   '#2a2d3a',
    'text':          '#e8eaed',
    'text_secondary':'#8b8fa3',
    'accent':        '#4fc3f7',
    'red':           '#ef5350',
    'green':         '#66bb6a',
    'gold':          '#ffd54f',
    'purple':        '#ab47bc',
    'orange':        '#ff9800',
    'header_bg':     'linear-gradient(135deg, #1a237e 0%, #0d47a1 50%, #006064 100%)',
}


def _change_color(pct: float) -> str:
    if pct > 0: return COLORS['red']
    elif pct < 0: return COLORS['green']
    return COLORS['text']


def _change_sign(pct: float) -> str:
    if pct > 0: return f"+{pct:.2f}%"
    elif pct < 0: return f"{pct:.2f}%"
    return "0.00%"


def _format_amount(val: float) -> str:
    if val >= 1e12: return f"{val / 1e12:.2f}万亿"
    elif val >= 1e8: return f"{val / 1e8:.2f}亿"
    elif val >= 1e4: return f"{val / 1e4:.2f}万"
    return f"{val:.0f}"


def _pct_bar_html(pct: float, max_pct: float = 10) -> str:
    color = _change_color(pct)
    width = min(abs(pct) / max_pct * 100, 100)
    return f'<div style="width:{width}%;background:{color};border-radius:4px;" class="bar-fill"></div>'


def _signal_badge(signal: str, color: str) -> str:
    """生成信号标签"""
    c = COLORS.get(color, COLORS['text'])
    return f'<span class="signal-badge" style="background:{c}22;color:{c};border:1px solid {c}44">{signal}</span>'


# ============================================================
# 分析函数
# ============================================================

def analyze_market_sentiment(indices: List[Dict], stocks: List[Dict]) -> Dict[str, Any]:
    """分析市场整体情绪"""
    if not indices:
        return {"score": 50, "label": "数据不足", "desc": "无指数数据", "color": COLORS['text_secondary']}

    # 指数得分
    idx_scores = []
    for idx in indices:
        pct = idx.get("change_pct", 0)
        if pct > 1: idx_scores.append(80)
        elif pct > 0.3: idx_scores.append(65)
        elif pct > 0: idx_scores.append(55)
        elif pct > -0.3: idx_scores.append(45)
        elif pct > -1: idx_scores.append(35)
        else: idx_scores.append(20)

    avg_idx = sum(idx_scores) / len(idx_scores) if idx_scores else 50

    # 个股得分
    stock_signals = [s.get("score", 50) for s in stocks]
    avg_stock = sum(stock_signals) / len(stock_signals) if stock_signals else 50

    # 综合得分（指数权重60%，个股权重40%）
    sentiment_score = round(avg_idx * 0.6 + avg_stock * 0.4)

    if sentiment_score >= 70:
        label, desc, color = "偏多", "多数指数上涨，市场情绪积极", COLORS['red']
    elif sentiment_score >= 55:
        label, desc, color = "中性偏多", "指数分化，整体略偏乐观", COLORS['orange']
    elif sentiment_score >= 45:
        label, desc, color = "中性", "市场涨跌互现，方向不明", COLORS['gold']
    elif sentiment_score >= 30:
        label, desc, color = "中性偏空", "多数指数下跌，需谨慎", COLORS['text_secondary']
    else:
        label, desc, color = "偏空", "市场普遍下跌，风险较高", COLORS['green']

    return {
        "score": sentiment_score,
        "label": label,
        "desc": desc,
        "color": color,
        "idx_avg": round(avg_idx, 1),
        "stock_avg": round(avg_stock, 1),
    }


def analyze_index_trend(indices: List[Dict]) -> List[Dict]:
    """分析指数趋势"""
    results = []
    for idx in indices:
        above_ma5 = idx.get("above_ma5", False)
        above_ma3 = idx.get("above_ma3", False)
        pct = idx.get("change_pct", 0)
        hist = idx.get("history_5d", [])

        if above_ma5 and pct > 0:
            trend = "上升趋势"
            trend_color = COLORS['red']
        elif not above_ma5 and pct < 0:
            trend = "下降趋势"
            trend_color = COLORS['green']
        elif above_ma5:
            trend = "短期回调"
            trend_color = COLORS['gold']
        elif pct > 0:
            trend = "触底反弹"
            trend_color = COLORS['orange']
        else:
            trend = "震荡整理"
            trend_color = COLORS['text_secondary']

        results.append({
            **idx,
            "trend": trend,
            "trend_color": trend_color,
            "ma5_status": "站上" if above_ma5 else "跌破",
        })
    return results


def generate_analysis_summary(indices: List[Dict], stocks: List[Dict], sectors: List[Dict], sentiment: Dict) -> str:
    """生成文字分析总结"""
    lines = []

    # 1. 市场情绪
    lines.append(f"📌 **市场情绪：{sentiment['label']}**（综合评分 {sentiment['score']}/100）")
    lines.append(f"   {sentiment['desc']}")

    # 2. 指数分析
    if indices:
        strong_idx = [i for i in indices if i.get("change_pct", 0) > 0.5]
        weak_idx = [i for i in indices if i.get("change_pct", 0) < -0.5]
        if strong_idx:
            names = "、".join([f"{i['name']}({i['change_pct']:+.2f}%)" for i in strong_idx[:3]])
            lines.append(f"📈 **领涨指数**：{names}")
        if weak_idx:
            names = "、".join([f"{i['name']}({i['change_pct']:+.2f}%)" for i in weak_idx[:3]])
            lines.append(f"📉 **领跌指数**：{names}")

    # 3. 个股信号
    strong_stocks = [s for s in stocks if s.get("score", 0) >= 70]
    weak_stocks = [s for s in stocks if s.get("score", 0) <= 30]
    if strong_stocks:
        names = "、".join([f"{s['name']}({s['signal']})" for s in strong_stocks[:3]])
        lines.append(f"🔥 **强势个股**：{names}")
    if weak_stocks:
        names = "、".join([f"{s['name']}({s['signal']})" for s in weak_stocks[:3]])
        lines.append(f"⚠️ **弱势个股**：{names}")

    # 4. 板块亮点
    if sectors:
        top_sectors = sectors[:3]
        names = "、".join([f"{s['name']}({s['change_pct']:+.2f}%)" for s in top_sectors])
        lines.append(f"🏢 **活跃板块ETF**：{names}")

    # 5. 建议
    lines.append("")
    if sentiment['score'] >= 65:
        lines.append("💡 **操作建议**：市场整体偏强，可关注强势股回调机会，控制仓位不超过7成。")
    elif sentiment['score'] >= 45:
        lines.append("💡 **操作建议**：市场方向不明，建议观望为主，轻仓操作，注意风险控制。")
    else:
        lines.append("💡 **操作建议**：市场偏弱，建议降低仓位，关注超跌反弹机会，严格止损。")

    lines.append("")
    lines.append("_⚠️ 以上分析仅基于技术指标，不构成投资建议。_")

    return "\n".join(lines)


# ============================================================
# 迷你折线图（纯 CSS + inline SVG）
# ============================================================

def _mini_chart_svg(data_points: List[float], width: int = 120, height: int = 40) -> str:
    """生成迷你折线图 SVG"""
    if len(data_points) < 2:
        return ""

    min_val = min(data_points)
    max_val = max(data_points)
    val_range = max_val - min_val if max_val != min_val else 1

    points = []
    for i, val in enumerate(data_points):
        x = (i / (len(data_points) - 1)) * width
        y = height - ((val - min_val) / val_range) * (height - 4) - 2
        points.append(f"{x:.1f},{y:.1f}")

    # 判断涨跌颜色
    color = COLORS['red'] if data_points[-1] >= data_points[0] else COLORS['green']

    return f'''<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" style="display:block">
  <polyline points="{' '.join(points)}" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
  <circle cx="{points[-1].split(',')[0]}" cy="{points[-1].split(',')[1]}" r="3" fill="{color}"/>
</svg>'''


# ============================================================
# 主 HTML 生成
# ============================================================

def generate_stock_html(data: Dict[str, Any]) -> str:
    """生成完整的股市仪表盘 HTML（含分析）"""

    overview = data.get("overview", {})
    indices = data.get("indices", [])
    stocks = data.get("stocks", [])
    sectors = data.get("sectors", [])
    north_flow = data.get("north_flow", [])
    gen_time = data.get("generated_at", "")
    gen_time_utc = data.get("generated_at_utc", "")
    # 自选股配置（用于前端管理面板）
    watchlist_config = data.get("watchlist_config", {})
    default_stocks = watchlist_config.get("自选股", [{"code": s.get("code",""), "name": s.get("name",""), "market": s.get("market","sh")} for s in stocks])
    default_watchlist_json = json.dumps(default_stocks, ensure_ascii=False)
    full_watchlist_json = json.dumps(watchlist_config, ensure_ascii=False, indent=4)

    total_up = overview.get("total_up", 0)
    total_down = overview.get("total_down", 0)
    total_flat = overview.get("total_flat", 0)
    limit_up = overview.get("limit_up", 0)
    limit_down = overview.get("limit_down", 0)
    total_stocks = overview.get("total_stocks", 0)

    # ============ 分析 ============
    sentiment = analyze_market_sentiment(indices, stocks)
    index_trends = analyze_index_trend(indices)
    analysis_text = generate_analysis_summary(indices, stocks, sectors, sentiment)

    # ============ 指数卡片（含趋势） ============
    index_cards = ""
    for idx in index_trends[:6]:
        color = _change_color(idx.get("change_pct", 0))
        sign = _change_sign(idx.get("change_pct", 0))
        trend = idx.get("trend", "震荡")
        trend_color = idx.get("trend_color", COLORS['text_secondary'])
        chart = _mini_chart_svg(idx.get("history_5d", []))
        ma5_status = idx.get("ma5_status", "--")
        index_cards += f"""
        <div class="idx-card">
            <div style="display:flex;justify-content:space-between;align-items:center">
                <div class="idx-name">{idx['name']}</div>
                <span class="trend-tag" style="color:{trend_color};background:{trend_color}18;border:1px solid {trend_color}33">{trend}</span>
            </div>
            <div class="idx-price" style="color:{color}">{idx.get('price', '--')}</div>
            <div class="idx-change" style="color:{color}">{sign}</div>
            <div style="display:flex;justify-content:space-between;align-items:center;margin-top:6px">
                <div class="idx-amount">MA5 {ma5_status}</div>
                <div>{chart}</div>
            </div>
        </div>"""

    # ============ 自选股表格（含信号+技术指标） ============
    stock_rows = ""
    for s in sorted(stocks, key=lambda x: x.get("score", 50), reverse=True):
        color = _change_color(s.get("change_pct", 0))
        sign = _change_sign(s.get("change_pct", 0))
        signal = s.get("signal", "中性")
        signal_color = s.get("signal_color", "gray")
        rsi = s.get("rsi", 50)
        vol_ratio = s.get("vol_ratio", 1.0)
        amplitude = s.get("amplitude", 0)
        macd_hist = s.get("macd_hist", 0)
        j_val = s.get("j", 50)
        chart = _mini_chart_svg(s.get("history_5d", []), 80, 30)

        # MACD柱颜色
        macd_color = COLORS['red'] if macd_hist > 0 else COLORS['green'] if macd_hist < 0 else COLORS['text_secondary']
        # KDJ J值颜色
        j_color = COLORS['red'] if j_val > 80 else COLORS['green'] if j_val < 20 else COLORS['text_secondary']

        stock_rows += f"""
        <tr>
            <td class="stock-name">{s['name']}</td>
            <td style="font-size:12px;color:{COLORS['text_secondary']}">{s['code']}</td>
            <td class="num" style="color:{color};font-weight:600">{s.get('price', '--')}</td>
            <td class="num" style="color:{color}">{sign}</td>
            <td>{_signal_badge(signal, signal_color)}</td>
            <td class="num" style="font-size:12px;color:{COLORS['accent']}">{rsi:.0f}</td>
            <td class="num" style="font-size:12px;color:{macd_color}">{macd_hist:+.3f}</td>
            <td class="num" style="font-size:12px;color:{j_color}">{j_val:.0f}</td>
            <td class="num" style="font-size:12px">{vol_ratio:.1f}</td>
            <td>{chart}</td>
        </tr>"""

    # ============ 技术指标详情卡片 ============
    tech_detail_cards = ""
    for s in sorted(stocks, key=lambda x: x.get("score", 50), reverse=True):
        bb_upper = s.get("bb_upper", 0)
        bb_middle = s.get("bb_middle", 0)
        bb_lower = s.get("bb_lower", 0)
        bb_pos = s.get("bb_position", 50)
        price = s.get("price", 0)
        macd_val = s.get("macd", 0)
        macd_signal = s.get("macd_signal", 0)
        macd_hist_val = s.get("macd_hist", 0)
        k_val = s.get("k", 50)
        d_val = s.get("d", 50)
        j_val = s.get("j", 50)

        # 布林带进度
        bb_pct = max(0, min(100, bb_pos))
        # MACD柱方向
        macd_bar_color = COLORS['red'] if macd_hist_val > 0 else COLORS['green']
        # KDJ判断
        if j_val > 80: kdj_signal = "超买区"
        elif j_val > 50: kdj_signal = "偏强"
        elif j_val > 20: kdj_signal = "偏弱"
        else: kdj_signal = "超卖区"
        kdj_color = COLORS['red'] if j_val > 50 else COLORS['green']

        tech_detail_cards += f"""
        <div class="tech-card">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
                <span style="font-weight:600;font-size:14px">{s['name']}</span>
                <span class="num" style="font-size:13px;font-weight:600;color:{_change_color(s.get('change_pct',0))}">{s.get('price','--')}</span>
            </div>
            <div class="tech-row"><span class="tech-label">MACD</span>
                <span class="num" style="font-size:11px;color:{COLORS['accent']}">DIF:{macd_val:.3f}</span>
                <span class="num" style="font-size:11px;color:{COLORS['text_secondary']}">DEA:{macd_signal:.3f}</span>
                <span class="num" style="font-size:11px;color:{macd_bar_color};font-weight:600">柱:{macd_hist_val:+.3f}</span>
            </div>
            <div class="tech-row"><span class="tech-label">KDJ</span>
                <span class="num" style="font-size:11px">K:{k_val:.0f} D:{d_val:.0f}</span>
                <span class="num" style="font-size:11px;color:{kdj_color};font-weight:600">J:{j_val:.0f}({kdj_signal})</span>
            </div>
            <div class="tech-row"><span class="tech-label">布林带</span>
                <span class="num" style="font-size:11px;color:{COLORS['red']}">{bb_upper}</span>
                <span class="num" style="font-size:11px;color:{COLORS['text_secondary']}">{bb_middle}</span>
                <span class="num" style="font-size:11px;color:{COLORS['green']}">{bb_lower}</span>
            </div>
            <div class="bb-bar"><div class="bb-bar-fill" style="width:{bb_pct}%;left:{bb_pct * 0.8}%"></div>
                <div class="bb-marker" style="left:{bb_pct}%">{price}</div></div>
        </div>"""

    # ============ 板块排名（ETF替代） ============
    sector_rows = ""
    if sectors:
        max_sector_pct = max(abs(s.get("change_pct", 0)) for s in sectors) or 1
        for s in sectors:
            color = _change_color(s.get("change_pct", 0))
            sign = _change_sign(s.get("change_pct", 0))
            bar = _pct_bar_html(s.get("change_pct", 0), max_sector_pct)
            etype = s.get("type", "")
            sector_rows += f"""
        <tr>
            <td class="sector-name">{s['name']}<span style="font-size:10px;color:{COLORS['text_secondary']};margin-left:4px">{etype}</span></td>
            <td class="num" style="color:{color};font-weight:600;width:80px">{sign}</td>
            <td style="width:200px"><div class="bar-container">{bar}</div></td>
        </tr>"""

    # ============ 北向资金 ============
    north_rows = ""
    for n in north_flow:
        color = COLORS['red'] if n.get("net_buy", 0) > 0 else COLORS['green'] if n.get("net_buy", 0) < 0 else COLORS['text']
        val = n.get("net_buy", 0)
        north_rows += f"""
        <tr>
            <td>{n.get('date', '')}</td>
            <td class="num" style="color:{color};font-weight:600">{'+' if val > 0 else ''}{val:.2f} 亿</td>
        </tr>"""

    # ============ 涨跌比 ============
    up_ratio = total_up / max(total_up + total_down, 1) * 100
    down_ratio = total_down / max(total_up + total_down, 1) * 100

    # ============ 情绪仪表盘 SVG ============
    sentiment_score = sentiment['score']
    gauge_angle = (sentiment_score / 100) * 180  # 0-180度
    gauge_color = sentiment['color']

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>A股行情仪表盘 | 自动更新</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
    background: {COLORS['bg']};
    color: {COLORS['text']};
    line-height: 1.6;
    min-height: 100vh;
}}
.container {{ max-width: 1200px; margin: 0 auto; padding: 16px; }}

/* ---- Header ---- */
.header {{
    text-align: center;
    padding: 40px 24px 32px;
    background: {COLORS['header_bg']};
    border-radius: 16px;
    margin-bottom: 24px;
    position: relative;
    overflow: hidden;
}}
.header::before {{
    content: '';
    position: absolute;
    top: -50%; left: -50%;
    width: 200%; height: 200%;
    background: radial-gradient(circle, rgba(255,255,255,0.04) 0%, transparent 60%);
    animation: rotate 25s linear infinite;
}}
@keyframes rotate {{ from {{ transform: rotate(0deg); }} to {{ transform: rotate(360deg); }} }}
.header h1 {{ font-size: 28px; font-weight: 700; position: relative; }}
.header p {{ color: rgba(255,255,255,0.7); margin-top: 8px; font-size: 14px; position: relative; }}

/* ---- Cards ---- */
.card {{
    background: {COLORS['card_bg']};
    border: 1px solid {COLORS['card_border']};
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 20px;
}}
.card-title {{
    font-size: 18px;
    font-weight: 600;
    margin-bottom: 16px;
    padding-bottom: 12px;
    border-bottom: 1px solid {COLORS['card_border']};
    display: flex;
    align-items: center;
    gap: 8px;
}}
.card-title .icon {{ font-size: 20px; }}

/* ---- Market Overview ---- */
.overview-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 12px;
}}
.stat-box {{
    text-align: center;
    padding: 16px 12px;
    border-radius: 10px;
    background: rgba(255,255,255,0.03);
}}
.stat-value {{ font-size: 28px; font-weight: 700; }}
.stat-label {{ font-size: 12px; color: {COLORS['text_secondary']}; margin-top: 4px; }}
.stat-up .stat-value {{ color: {COLORS['red']}; }}
.stat-down .stat-value {{ color: {COLORS['green']}; }}
.stat-flat .stat-value {{ color: {COLORS['gold']}; }}

/* ---- Ratio Bar ---- */
.ratio-bar {{
    height: 8px; border-radius: 4px; overflow: hidden; display: flex;
    margin-top: 12px; background: {COLORS['card_border']};
}}
.ratio-up {{ background: {COLORS['red']}; width: {up_ratio:.1f}%; }}
.ratio-down {{ background: {COLORS['green']}; width: {down_ratio:.1f}%; }}
.ratio-label {{ display: flex; justify-content: space-between; font-size: 12px; color: {COLORS['text_secondary']}; margin-top: 6px; }}

/* ---- Sentiment ---- */
.sentiment-section {{
    display: grid;
    grid-template-columns: 200px 1fr;
    gap: 24px;
    align-items: center;
}}
.sentiment-gauge {{
    text-align: center;
}}
.sentiment-score {{
    font-size: 48px;
    font-weight: 800;
    color: {gauge_color};
    line-height: 1;
}}
.sentiment-label {{
    font-size: 16px;
    font-weight: 600;
    margin-top: 8px;
    color: {gauge_color};
}}
.sentiment-desc {{
    font-size: 13px;
    color: {COLORS['text_secondary']};
    margin-top: 4px;
}}
.sentiment-bar-bg {{
    width: 100%;
    height: 10px;
    border-radius: 5px;
    background: {COLORS['card_border']};
    margin-top: 12px;
    overflow: hidden;
}}
.sentiment-bar-fill {{
    height: 100%;
    border-radius: 5px;
    width: {sentiment_score}%;
    background: linear-gradient(90deg, {COLORS['green']}, {COLORS['gold']} 50%, {COLORS['red']});
}}
.analysis-text {{
    font-size: 14px;
    line-height: 2;
    color: {COLORS['text']};
}}
.analysis-text strong {{
    color: {COLORS['accent']};
    font-weight: 600;
}}
.analysis-text em {{
    color: {COLORS['text_secondary']};
    font-style: italic;
    font-size: 12px;
}}

/* ---- Index Cards ---- */
.index-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 12px;
}}
.idx-card {{
    padding: 14px;
    border-radius: 10px;
    background: rgba(255,255,255,0.03);
    border: 1px solid {COLORS['card_border']};
}}
.idx-name {{ font-size: 13px; color: {COLORS['text_secondary']}; }}
.idx-price {{ font-size: 22px; font-weight: 700; margin-top: 4px; }}
.idx-change {{ font-size: 14px; font-weight: 600; margin-top: 2px; }}
.idx-amount {{ font-size: 11px; color: {COLORS['text_secondary']}; margin-top: 4px; }}
.trend-tag {{
    font-size: 10px;
    padding: 2px 6px;
    border-radius: 4px;
    font-weight: 600;
}}

/* ---- Tables ---- */
table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
th {{
    text-align: left;
    padding: 10px 8px;
    font-weight: 600;
    color: {COLORS['text_secondary']};
    font-size: 11px;
    text-transform: uppercase;
    border-bottom: 1px solid {COLORS['card_border']};
    white-space: nowrap;
}}
td {{
    padding: 10px 8px;
    border-bottom: 1px solid rgba(255,255,255,0.04);
    white-space: nowrap;
}}
.stock-name {{ font-weight: 600; }}
.sector-name {{ font-weight: 500; }}
.num {{ font-variant-numeric: tabular-nums; text-align: right; }}
tr:hover {{ background: rgba(255,255,255,0.03); }}

/* ---- Signal Badge ---- */
.signal-badge {{
    font-size: 11px;
    padding: 2px 8px;
    border-radius: 10px;
    font-weight: 600;
    white-space: nowrap;
}}

/* ---- Bar ---- */
.bar-container {{
    height: 6px;
    background: rgba(255,255,255,0.05);
    border-radius: 3px;
    overflow: hidden;
}}
.bar-fill {{ height: 100%; min-width: 2px; transition: width 0.3s; }}

/* ---- Two Column ---- */
.two-col {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
}}

/* ---- Responsive ---- */
@media (max-width: 768px) {{
    .two-col {{ grid-template-columns: 1fr; }}
    .sentiment-section {{ grid-template-columns: 1fr; }}
    .index-grid {{ grid-template-columns: repeat(2, 1fr); }}
    .overview-grid {{ grid-template-columns: repeat(2, 1fr); }}
    .container {{ padding: 8px; }}
    .header h1 {{ font-size: 22px; }}
    .sentiment-score {{ font-size: 36px; }}
}}

/* ---- Tech Detail Card ---- */
.tech-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    gap: 12px;
}}
.tech-card {{
    padding: 14px;
    border-radius: 10px;
    background: rgba(255,255,255,0.03);
    border: 1px solid {COLORS['card_border']};
}}
.tech-row {{
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 12px;
    margin-bottom: 6px;
}}
.tech-label {{
    font-weight: 600;
    color: {COLORS['text_secondary']};
    min-width: 50px;
}}
.bb-bar {{
    position: relative;
    height: 8px;
    border-radius: 4px;
    background: linear-gradient(90deg, {COLORS['green']}33, {COLORS['gold']}33 50%, {COLORS['red']}33);
    margin-top: 6px;
}}
.bb-marker {{
    position: absolute;
    top: -6px;
    transform: translateX(-50%);
    font-size: 10px;
    font-weight: 600;
    color: {COLORS['accent']};
    white-space: nowrap;
}}

/* ---- Footer ---- */
.footer {{
    text-align: center;
    padding: 20px;
    font-size: 12px;
    color: {COLORS['text_secondary']};
}}
.disclaimer {{
    background: rgba(255, 215, 0, 0.08);
    border: 1px solid rgba(255, 215, 0, 0.2);
    border-radius: 8px;
    padding: 12px;
    margin-top: 16px;
    font-size: 12px;
    color: {COLORS['gold']};
    text-align: center;
}}

/* ---- 自选股管理按钮 ---- */
.manage-btn {{
    position: fixed;
    top: 16px;
    right: 16px;
    z-index: 1000;
    background: linear-gradient(135deg, #1565c0, #0d47a1);
    color: #fff;
    border: none;
    border-radius: 8px;
    padding: 10px 16px;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    box-shadow: 0 4px 16px rgba(21,101,192,0.4);
    display: flex;
    align-items: center;
    gap: 6px;
    transition: all 0.2s;
    font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', sans-serif;
}}
.manage-btn:hover {{ transform: translateY(-2px); box-shadow: 0 6px 20px rgba(21,101,192,0.5); }}

/* ---- 自选股管理遮罩 ---- */
.watchlist-overlay {{
    display: none;
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.7);
    z-index: 1001;
    align-items: center;
    justify-content: center;
}}
.watchlist-overlay.open {{ display: flex; }}

/* ---- 管理面板 ---- */
.watchlist-panel {{
    background: #1a1d29;
    border: 1px solid #2a2d3a;
    border-radius: 16px;
    width: 90%;
    max-width: 560px;
    max-height: 85vh;
    display: flex;
    flex-direction: column;
    box-shadow: 0 24px 60px rgba(0,0,0,0.6);
    overflow: hidden;
}}
.wl-header {{
    padding: 20px 24px 16px;
    border-bottom: 1px solid #2a2d3a;
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-shrink: 0;
}}
.wl-title {{ font-size: 18px; font-weight: 700; color: #e8eaed; }}
.wl-close {{
    width: 32px; height: 32px;
    background: rgba(255,255,255,0.08);
    border: none; border-radius: 8px;
    color: #8b8fa3; font-size: 18px;
    cursor: pointer; display: flex; align-items: center; justify-content: center;
    transition: all 0.15s;
}}
.wl-close:hover {{ background: rgba(255,255,255,0.15); color: #e8eaed; }}

/* ---- 添加区域 ---- */
.wl-add-area {{
    padding: 16px 24px;
    border-bottom: 1px solid #2a2d3a;
    flex-shrink: 0;
}}
.wl-add-title {{ font-size: 13px; font-weight: 600; color: #8b8fa3; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 0.5px; }}
.wl-add-row {{ display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }}
.wl-input {{
    flex: 1;
    min-width: 100px;
    background: rgba(255,255,255,0.06);
    border: 1px solid #3a3d4a;
    border-radius: 8px;
    padding: 8px 12px;
    color: #e8eaed;
    font-size: 13px;
    outline: none;
    font-family: inherit;
    transition: border-color 0.15s;
}}
.wl-input:focus {{ border-color: #4fc3f7; }}
.wl-input::placeholder {{ color: #555; }}
.wl-select {{
    background: rgba(255,255,255,0.06);
    border: 1px solid #3a3d4a;
    border-radius: 8px;
    padding: 8px 10px;
    color: #e8eaed;
    font-size: 13px;
    outline: none;
    cursor: pointer;
    font-family: inherit;
}}
.wl-add-btn {{
    background: #1565c0;
    border: none;
    border-radius: 8px;
    padding: 8px 16px;
    color: #fff;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    white-space: nowrap;
    font-family: inherit;
    transition: background 0.15s;
}}
.wl-add-btn:hover {{ background: #1976d2; }}
.wl-hint {{ font-size: 11px; color: #555; margin-top: 8px; }}

/* ---- 股票列表 ---- */
.wl-list {{
    flex: 1;
    overflow-y: auto;
    padding: 12px 24px;
}}
.wl-list::-webkit-scrollbar {{ width: 6px; }}
.wl-list::-webkit-scrollbar-track {{ background: transparent; }}
.wl-list::-webkit-scrollbar-thumb {{ background: #2a2d3a; border-radius: 3px; }}
.wl-item {{
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 12px;
    border-radius: 10px;
    border: 1px solid transparent;
    margin-bottom: 6px;
    transition: all 0.15s;
}}
.wl-item:hover {{ background: rgba(255,255,255,0.04); border-color: #2a2d3a; }}
.wl-item.custom {{ border-color: #1565c044; background: rgba(21,101,192,0.06); }}
.wl-tag {{
    font-size: 10px;
    padding: 1px 6px;
    border-radius: 4px;
    font-weight: 600;
}}
.wl-tag.sh {{ background: #ef535020; color: #ef5350; }}
.wl-tag.sz {{ background: #66bb6a20; color: #66bb6a; }}
.wl-tag.new {{ background: #4fc3f720; color: #4fc3f7; }}
.wl-item-name {{ font-size: 14px; font-weight: 600; color: #e8eaed; flex: 1; }}
.wl-item-code {{ font-size: 12px; color: #8b8fa3; }}
.wl-del-btn {{
    width: 28px; height: 28px;
    background: rgba(239,83,80,0.1);
    border: 1px solid rgba(239,83,80,0.2);
    border-radius: 6px;
    color: #ef5350;
    font-size: 16px;
    cursor: pointer;
    display: flex; align-items: center; justify-content: center;
    transition: all 0.15s;
    flex-shrink: 0;
}}
.wl-del-btn:hover {{ background: rgba(239,83,80,0.25); border-color: rgba(239,83,80,0.5); }}

/* ---- 底部操作 ---- */
.wl-footer {{
    padding: 16px 24px;
    border-top: 1px solid #2a2d3a;
    display: flex;
    gap: 10px;
    flex-shrink: 0;
}}
.wl-export-btn {{
    flex: 1;
    background: rgba(255,255,255,0.06);
    border: 1px solid #3a3d4a;
    border-radius: 8px;
    padding: 10px;
    color: #8b8fa3;
    font-size: 13px;
    cursor: pointer;
    font-family: inherit;
    transition: all 0.15s;
}}
.wl-export-btn:hover {{ color: #e8eaed; border-color: #8b8fa3; }}
.wl-reset-btn {{
    background: rgba(239,83,80,0.1);
    border: 1px solid rgba(239,83,80,0.2);
    border-radius: 8px;
    padding: 10px 14px;
    color: #ef5350;
    font-size: 13px;
    cursor: pointer;
    font-family: inherit;
    transition: all 0.15s;
}}
.wl-reset-btn:hover {{ background: rgba(239,83,80,0.2); }}
.wl-toast {{
    position: fixed;
    bottom: 32px;
    left: 50%;
    transform: translateX(-50%) translateY(20px);
    background: #1e2a3a;
    border: 1px solid #4fc3f7;
    color: #4fc3f7;
    padding: 10px 20px;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 600;
    z-index: 9999;
    opacity: 0;
    transition: all 0.3s;
    pointer-events: none;
    font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', sans-serif;
}}
.wl-toast.show {{ opacity: 1; transform: translateX(-50%) translateY(0); }}

/* 自定义股票行高亮 */
.custom-stock-row {{ background: rgba(21,101,192,0.06); }}
</style>
</head>
<body>

<!-- 自选股管理按钮（固定右上角） -->
<button class="manage-btn" onclick="openWatchlistPanel()">
    <span>⭐</span> 管理自选股
</button>

<!-- 自选股管理弹窗 -->
<div class="watchlist-overlay" id="watchlistOverlay" onclick="handleOverlayClick(event)">
    <div class="watchlist-panel">
        <div class="wl-header">
            <span class="wl-title">⭐ 管理自选股</span>
            <button class="wl-close" onclick="closeWatchlistPanel()">✕</button>
        </div>
        <div class="wl-add-area">
            <div class="wl-add-title">➕ 添加股票</div>
            <div class="wl-add-row">
                <select class="wl-select" id="addMarket">
                    <option value="sh">沪市 (sh)</option>
                    <option value="sz">深市 (sz)</option>
                </select>
                <input class="wl-input" id="addCode" placeholder="股票代码，如 600519" maxlength="6" />
                <input class="wl-input" id="addName" placeholder="名称，如 贵州茅台" maxlength="10" />
                <button class="wl-add-btn" onclick="addStock()">添加</button>
            </div>
            <div class="wl-hint">💡 添加后下次 Actions 自动运行时会获取最新数据（约每30分钟）</div>
        </div>
        <div class="wl-list" id="watchlistItems"></div>
        <div class="wl-footer">
            <button class="wl-export-btn" onclick="exportConfig()">📥 导出 watchlist.json（放入仓库触发更新）</button>
            <button class="wl-reset-btn" onclick="resetToDefault()">恢复默认</button>
        </div>
    </div>
</div>

<!-- Toast 提示 -->
<div class="wl-toast" id="wlToast"></div>

<div class="container">

<!-- Header -->
<div class="header">
    <h1>A 股行情仪表盘</h1>
    <p>数据来源: Yahoo Finance &middot; 自动更新 &middot; <span id="update-time">{gen_time}</span></p>
</div>

<!-- Market Overview -->
<div class="card">
    <div class="card-title"><span class="icon">📈</span> 市场总览</div>
    <div class="overview-grid">
        <div class="stat-box stat-up">
            <div class="stat-value">{total_up}</div>
            <div class="stat-label">上涨</div>
        </div>
        <div class="stat-box stat-down">
            <div class="stat-value">{total_down}</div>
            <div class="stat-label">下跌</div>
        </div>
        <div class="stat-box stat-flat">
            <div class="stat-value">{total_flat}</div>
            <div class="stat-label">平盘</div>
        </div>
        <div class="stat-box stat-up">
            <div class="stat-value">{limit_up}</div>
            <div class="stat-label">涨停</div>
        </div>
        <div class="stat-box stat-down">
            <div class="stat-value">{limit_down}</div>
            <div class="stat-label">跌停</div>
        </div>
        <div class="stat-box">
            <div class="stat-value">{total_stocks}</div>
            <div class="stat-label">总计</div>
        </div>
    </div>
    <div class="ratio-bar">
        <div class="ratio-up"></div>
        <div class="ratio-down"></div>
    </div>
    <div class="ratio-label">
        <span>上涨 {up_ratio:.1f}%</span>
        <span>下跌 {down_ratio:.1f}%</span>
    </div>
</div>

<!-- 🆕 市场情绪分析 -->
<div class="card">
    <div class="card-title"><span class="icon">🧠</span> 市场情绪分析</div>
    <div class="sentiment-section">
        <div class="sentiment-gauge">
            <div class="sentiment-score">{sentiment_score}</div>
            <div class="sentiment-label">{sentiment['label']}</div>
            <div class="sentiment-desc">{sentiment['desc']}</div>
            <div class="sentiment-bar-bg">
                <div class="sentiment-bar-fill"></div>
            </div>
        </div>
        <div class="analysis-text">
{analysis_text}
        </div>
    </div>
</div>

<!-- Indices (with trend) -->
<div class="card">
    <div class="card-title"><span class="icon">📊</span> 主要指数 <span style="font-size:12px;color:{COLORS['text_secondary']};font-weight:400;margin-left:auto">含趋势分析 & 5日走势</span></div>
    <div class="index-grid">
        {index_cards}
    </div>
</div>

<!-- Technical Indicator Details -->
<div class="card">
    <div class="card-title"><span class="icon">🔬</span> 技术指标详情 <span style="font-size:12px;color:{COLORS['text_secondary']};font-weight:400;margin-left:auto">MACD / KDJ / 布林带</span></div>
    <div class="tech-grid">
        {tech_detail_cards if tech_detail_cards else '<div style="text-align:center;color:#8b8fa3;padding:20px">暂无数据</div>'}
    </div>
</div>

<div class="two-col">
    <div class="card">
        <div class="card-title"><span class="icon">⭐</span> 自选股 <span style="font-size:12px;color:{COLORS['text_secondary']};font-weight:400">含技术信号</span>
            <span id="customStockHint" style="display:none;margin-left:8px;font-size:11px;background:#1565c022;color:#4fc3f7;border:1px solid #4fc3f744;padding:2px 8px;border-radius:4px;font-weight:400">含自定义配置，重启 Actions 后生效</span>
        </div>
        <div style="overflow-x:auto">
        <table>
            <thead>
                <tr>
                    <th>名称</th>
                    <th>代码</th>
                    <th style="text-align:right">价格</th>
                    <th style="text-align:right">涨跌</th>
                    <th>信号</th>
                    <th style="text-align:right">RSI</th>
                    <th style="text-align:right">MACD</th>
                    <th style="text-align:right">KDJ-J</th>
                    <th style="text-align:right">量比</th>
                    <th>5日</th>
                </tr>
            </thead>
            <tbody>
                {stock_rows if stock_rows else '<tr><td colspan="10" style="text-align:center;color:#8b8fa3">暂无数据</td></tr>'}
            </tbody>
        </table>
        </div>
    </div>

    <div class="card">
        <div class="card-title"><span class="icon">🏢</span> 板块 ETF 排名 <span style="font-size:12px;color:{COLORS['text_secondary']};font-weight:400;margin-left:auto">替代行业板块</span></div>
        <div style="overflow-x:auto">
        <table>
            <thead>
                <tr>
                    <th>ETF</th>
                    <th style="text-align:right">涨跌幅</th>
                    <th></th>
                </tr>
            </thead>
            <tbody>
                {sector_rows if sector_rows else '<tr><td colspan="3" style="text-align:center;color:#8b8fa3">暂无数据</td></tr>'}
            </tbody>
        </table>
        </div>
    </div>
</div>

<!-- North Flow -->
<div class="card">
    <div class="card-title"><span class="icon">💰</span> 北向资金流向（近5日）</div>
    <table>
        <thead>
            <tr>
                <th>日期</th>
                <th style="text-align:right">净买入（亿元）</th>
            </tr>
        </thead>
        <tbody>
            {north_rows if north_rows else '<tr><td colspan="2" style="text-align:center;color:#8b8fa3">暂无数据（yfinance 暂不支持北向资金接口）</td></tr>'}
        </tbody>
    </table>
</div>

<!-- 嵌入自选股完整配置（供 JS 导出使用） -->
<script id="fullWatchlistConfig" type="application/json">
__FULL_WATCHLIST_PLACEHOLDER__
</script>

<!-- Disclaimer -->
<div class="disclaimer">
    ⚠️ 本工具仅供学习参考，不构成任何投资建议。股市有风险，投资需谨慎。
</div>

<div class="footer">
    <p>由 GitHub Actions 自动生成 &middot; WorkBuddy AI</p>
    <p data-utc="{gen_time_utc}"></p>
</div>

</div>

<script>
// =====================================================
// 时间更新
// =====================================================
document.addEventListener('DOMContentLoaded', function() {{
    var utcStr = document.querySelector('.footer [data-utc]')?.dataset.utc;
    if (!utcStr) return;
    var utcDate = new Date(utcStr);
    function update() {{
        var diff = Math.floor((Date.now() - utcDate.getTime()) / 60000);
        var text;
        if (diff < 1) text = '刚刚更新';
        else if (diff < 60) text = diff + ' 分钟前更新';
        else if (diff < 1440) text = Math.floor(diff / 60) + ' 小时前更新';
        else text = Math.floor(diff / 1440) + ' 天前更新';
        document.getElementById('update-time').textContent = text;
    }}
    update();
    setInterval(update, 60000);
}});

// =====================================================
// 自选股管理
// =====================================================
const STORAGE_KEY = 'stockdash_watchlist';
const DEFAULT_WATCHLIST = __DEFAULT_WATCHLIST_PLACEHOLDER__;

function getWatchlist() {{
    try {{
        var saved = localStorage.getItem(STORAGE_KEY);
        if (saved) return JSON.parse(saved);
    }} catch(e) {{}}
    return null;
}}

function saveWatchlist(list) {{
    localStorage.setItem(STORAGE_KEY, JSON.stringify(list));
}}

function isCustomized() {{
    return !!localStorage.getItem(STORAGE_KEY);
}}

function openWatchlistPanel() {{
    document.getElementById('watchlistOverlay').classList.add('open');
    renderWatchlistItems();
}}

function closeWatchlistPanel() {{
    document.getElementById('watchlistOverlay').classList.remove('open');
    updatePageHint();
}}

function handleOverlayClick(e) {{
    if (e.target === document.getElementById('watchlistOverlay')) closeWatchlistPanel();
}}

function renderWatchlistItems() {{
    var current = getWatchlist() || DEFAULT_WATCHLIST;
    var defaultCodes = DEFAULT_WATCHLIST.map(s => s.market + s.code);
    var container = document.getElementById('watchlistItems');
    if (!current.length) {{
        container.innerHTML = '<div style="text-align:center;color:#555;padding:24px;font-size:13px">暂无自选股，请添加</div>';
        return;
    }}
    container.innerHTML = current.map(function(s, i) {{
        var isCustom = !defaultCodes.includes(s.market + s.code);
        var tagClass = s.market === 'sh' ? 'sh' : 'sz';
        var tagLabel = s.market === 'sh' ? '沪' : '深';
        return '<div class="wl-item' + (isCustom ? ' custom' : '') + '" data-index="' + i + '">'
            + '<span class="wl-tag ' + tagClass + '">' + tagLabel + '</span>'
            + '<span class="wl-item-name">' + escHtml(s.name) + '</span>'
            + '<span class="wl-item-code">' + s.code + '</span>'
            + (isCustom ? '<span class="wl-tag new">新</span>' : '')
            + '<button class="wl-del-btn" onclick="removeStock(' + i + ')" title="删除">×</button>'
            + '</div>';
    }}).join('');
}}

function addStock() {{
    var market = document.getElementById('addMarket').value;
    var code = document.getElementById('addCode').value.trim().replace(/\\D/g,'');
    var name = document.getElementById('addName').value.trim();
    if (!code || code.length < 4) {{ showToast('请输入有效的股票代码（4-6位数字）'); return; }}
    if (!name) {{ showToast('请输入股票名称'); return; }}
    var current = getWatchlist() || [...DEFAULT_WATCHLIST];
    if (current.some(s => s.market === market && s.code === code)) {{
        showToast('该股票已在自选股中'); return;
    }}
    if (current.length >= 20) {{ showToast('自选股最多20只'); return; }}
    current.push({{ code: code, name: name, market: market }});
    saveWatchlist(current);
    document.getElementById('addCode').value = '';
    document.getElementById('addName').value = '';
    renderWatchlistItems();
    showToast('✅ 已添加 ' + name + '，导出配置后放入仓库触发更新');
}}

function removeStock(index) {{
    var current = getWatchlist() || [...DEFAULT_WATCHLIST];
    var removed = current[index];
    current.splice(index, 1);
    saveWatchlist(current);
    renderWatchlistItems();
    showToast('已移除 ' + removed.name);
}}

function resetToDefault() {{
    if (!confirm('确定恢复为默认自选股配置吗？')) return;
    localStorage.removeItem(STORAGE_KEY);
    renderWatchlistItems();
    showToast('✅ 已恢复默认配置');
}}

function exportConfig() {{
    var current = getWatchlist() || DEFAULT_WATCHLIST;
    // 读取页面中嵌入的完整 watchlist（含指数和板块）
    var fullConfig = JSON.parse(document.getElementById('fullWatchlistConfig').textContent);
    fullConfig['自选股'] = current;
    var json = JSON.stringify(fullConfig, null, 4);
    var blob = new Blob([json], {{ type: 'application/json' }});
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url; a.download = 'watchlist.json';
    document.body.appendChild(a); a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showToast('📥 watchlist.json 已下载，放入 data/ 目录后 push 到 GitHub 触发更新');
}}

function updatePageHint() {{
    var hint = document.getElementById('customStockHint');
    if (hint) hint.style.display = isCustomized() ? 'inline' : 'none';
}}

function showToast(msg) {{
    var t = document.getElementById('wlToast');
    t.textContent = msg;
    t.classList.add('show');
    setTimeout(function() {{ t.classList.remove('show'); }}, 3000);
}}

function escHtml(s) {{
    return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}}

// 页面加载时检查自定义状态
document.addEventListener('DOMContentLoaded', function() {{
    updatePageHint();
    // ESC 关闭面板
    document.addEventListener('keydown', function(e) {{
        if (e.key === 'Escape') closeWatchlistPanel();
    }});
}});
</script>
</body>
</html>"""
    # 注入动态 JSON（不能放在 f-string 里，因为 JSON 含花括号）
    html = html.replace("__DEFAULT_WATCHLIST_PLACEHOLDER__", default_watchlist_json)
    html = html.replace("__FULL_WATCHLIST_PLACEHOLDER__", full_watchlist_json)
    return html


def save_report(html: str, output_path: str):
    """保存 HTML 报告到文件"""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"📄 报告已保存: {output_path}")
