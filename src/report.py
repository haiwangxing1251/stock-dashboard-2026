"""
股市仪表盘 — 自包含 HTML 报告生成器
=====================================
生成美观的中文股市仪表盘，纯 CSS/JS，无外部依赖。

模块:
- 市场总览（涨跌家数、涨停跌停）
- 主要指数行情
- 自选股行情
- 板块涨跌排名
- 北向资金流向
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
    'red':           '#ef5350',    # 涨（中国惯例）
    'green':         '#66bb6a',    # 跌
    'gold':          '#ffd54f',
    'header_bg':     'linear-gradient(135deg, #1a237e 0%, #0d47a1 50%, #006064 100%)',
}


def _change_color(pct: float) -> str:
    """根据涨跌幅返回颜色（红涨绿跌）"""
    if pct > 0:
        return COLORS['red']
    elif pct < 0:
        return COLORS['green']
    return COLORS['text']


def _change_sign(pct: float) -> str:
    """涨跌幅带符号"""
    if pct > 0:
        return f"+{pct:.2f}%"
    elif pct < 0:
        return f"{pct:.2f}%"
    return "0.00%"


def _format_amount(val: float) -> str:
    """格式化金额（亿元）"""
    if val >= 1e12:
        return f"{val / 1e12:.2f}万亿"
    elif val >= 1e8:
        return f"{val / 1e8:.2f}亿"
    elif val >= 1e4:
        return f"{val / 1e4:.2f}万"
    return f"{val:.0f}"


def _pct_bar_html(pct: float, max_pct: float = 10) -> str:
    """生成涨跌幅百分比条"""
    color = _change_color(pct)
    width = min(abs(pct) / max_pct * 100, 100)
    direction = "right" if pct > 0 else "left"
    return f'<div style="width:{width}%;background:{color};border-radius:4px;" class="bar-fill"></div>'


def generate_stock_html(data: Dict[str, Any]) -> str:
    """生成完整的股市仪表盘 HTML"""

    overview = data.get("overview", {})
    indices = data.get("indices", [])
    stocks = data.get("stocks", [])
    sectors = data.get("sectors", [])
    north_flow = data.get("north_flow", [])
    gen_time = data.get("generated_at", "")
    gen_time_utc = data.get("generated_at_utc", "")

    # 市场概况
    total_up = overview.get("total_up", 0)
    total_down = overview.get("total_down", 0)
    total_flat = overview.get("total_flat", 0)
    limit_up = overview.get("limit_up", 0)
    limit_down = overview.get("limit_down", 0)
    total_stocks = overview.get("total_stocks", 0)

    # 指数卡片
    index_cards = ""
    for idx in indices[:6]:
        color = _change_color(idx.get("change_pct", 0))
        sign = _change_sign(idx.get("change_pct", 0))
        index_cards += f"""
        <div class="idx-card">
            <div class="idx-name">{idx['name']}</div>
            <div class="idx-price" style="color:{color}">{idx.get('price', '--')}</div>
            <div class="idx-change" style="color:{color}">{sign}</div>
            <div class="idx-amount">成交 {_format_amount(idx.get('amount', 0))}</div>
        </div>"""

    # 自选股表格
    stock_rows = ""
    for s in sorted(stocks, key=lambda x: x.get("change_pct", 0), reverse=True):
        color = _change_color(s.get("change_pct", 0))
        sign = _change_sign(s.get("change_pct", 0))
        stock_rows += f"""
        <tr>
            <td class="stock-name">{s['name']}</td>
            <td>{s['code']}</td>
            <td class="num" style="color:{color}">{s.get('price', '--')}</td>
            <td class="num" style="color:{color};font-weight:600">{sign}</td>
            <td class="num">{_format_amount(s.get('amount', 0))}</td>
            <td class="num">{s.get('turnover_rate', 0):.1f}%</td>
            <td class="num">{s.get('pe', 0):.1f}</td>
        </tr>"""

    # 板块排名
    sector_rows = ""
    if sectors:
        max_sector_pct = max(abs(s.get("change_pct", 0)) for s in sectors) or 1
        for s in sectors:
            color = _change_color(s.get("change_pct", 0))
            sign = _change_sign(s.get("change_pct", 0))
            bar = _pct_bar_html(s.get("change_pct", 0), max_sector_pct)
            sector_rows += f"""
        <tr>
            <td class="sector-name">{s['name']}</td>
            <td class="num" style="color:{color};font-weight:600;width:80px">{sign}</td>
            <td style="width:200px"><div class="bar-container">{bar}</div></td>
        </tr>"""

    # 北向资金
    north_rows = ""
    for n in north_flow:
        color = COLORS['red'] if n.get("net_buy", 0) > 0 else COLORS['green'] if n.get("net_buy", 0) < 0 else COLORS['text']
        val = n.get("net_buy", 0)
        north_rows += f"""
        <tr>
            <td>{n.get('date', '')}</td>
            <td class="num" style="color:{color};font-weight:600">{'+' if val > 0 else ''}{val:.2f} 亿</td>
        </tr>"""

    # 涨跌比
    up_ratio = total_up / max(total_up + total_down, 1) * 100
    down_ratio = total_down / max(total_up + total_down, 1) * 100

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
    height: 8px;
    border-radius: 4px;
    overflow: hidden;
    display: flex;
    margin-top: 12px;
    background: {COLORS['card_border']};
}}
.ratio-up {{ background: {COLORS['red']}; width: {up_ratio:.1f}%; }}
.ratio-down {{ background: {COLORS['green']}; width: {down_ratio:.1f}%; }}
.ratio-label {{ display: flex; justify-content: space-between; font-size: 12px; color: {COLORS['text_secondary']}; margin-top: 6px; }}

/* ---- Index Cards ---- */
.index-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
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

/* ---- Tables ---- */
table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 14px;
}}
th {{
    text-align: left;
    padding: 10px 12px;
    font-weight: 600;
    color: {COLORS['text_secondary']};
    font-size: 12px;
    text-transform: uppercase;
    border-bottom: 1px solid {COLORS['card_border']};
}}
td {{
    padding: 10px 12px;
    border-bottom: 1px solid rgba(255,255,255,0.04);
}}
.stock-name {{ font-weight: 600; }}
.sector-name {{ font-weight: 500; }}
.num {{ font-variant-numeric: tabular-nums; text-align: right; }}
tr:hover {{ background: rgba(255,255,255,0.03); }}

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
@media (max-width: 768px) {{
    .two-col {{ grid-template-columns: 1fr; }}
    .index-grid {{ grid-template-columns: repeat(2, 1fr); }}
    .overview-grid {{ grid-template-columns: repeat(2, 1fr); }}
    .container {{ padding: 8px; }}
    .header h1 {{ font-size: 22px; }}
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
</style>
</head>
<body>
<div class="container">

<!-- Header -->
<div class="header">
    <h1>A 股行情仪表盘</h1>
    <p>数据来源: AKShare (东方财富) &middot; 自动更新 &middot; <span id="update-time">{gen_time}</span></p>
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

<!-- Indices -->
<div class="card">
    <div class="card-title"><span class="icon">📊</span> 主要指数</div>
    <div class="index-grid">
        {index_cards}
    </div>
</div>

<!-- Two Column: Stocks + Sectors -->
<div class="two-col">
    <div class="card">
        <div class="card-title"><span class="icon">⭐</span> 自选股 ({len(stocks)})</div>
        <div style="overflow-x:auto">
        <table>
            <thead>
                <tr>
                    <th>名称</th>
                    <th>代码</th>
                    <th style="text-align:right">价格</th>
                    <th style="text-align:right">涨跌幅</th>
                    <th style="text-align:right">成交额</th>
                    <th style="text-align:right">换手</th>
                    <th style="text-align:right">PE</th>
                </tr>
            </thead>
            <tbody>
                {stock_rows if stock_rows else '<tr><td colspan="7" style="text-align:center;color:#8b8fa3">暂无数据</td></tr>'}
            </tbody>
        </table>
        </div>
    </div>

    <div class="card">
        <div class="card-title"><span class="icon">🏭</span> 行业板块排名</div>
        <div style="overflow-x:auto">
        <table>
            <thead>
                <tr>
                    <th>板块</th>
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
            {north_rows if north_rows else '<tr><td colspan="2" style="text-align:center;color:#8b8fa3">暂无数据</td></tr>'}
        </tbody>
    </table>
</div>

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
// 动态显示"X分钟前"
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
</script>
</body>
</html>"""
    return html


def save_report(html: str, output_path: str):
    """保存 HTML 报告到文件"""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"📄 报告已保存: {output_path}")
