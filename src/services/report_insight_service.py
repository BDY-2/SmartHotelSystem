# -*- coding: utf-8 -*-
"""报表智能分析服务。"""


def build_report_insights(metrics, revenue_trend, room_type_revenue):
    """根据报表指标生成简短经营分析和建议。"""
    metrics = metrics or {}
    trend = revenue_trend or []
    room_revenue = room_type_revenue or {}
    insights = []

    values = [float(item.get("value", 0) or 0) for item in trend]
    if len(values) >= 2:
        first_half = values[:len(values) // 2]
        second_half = values[len(values) // 2:]
        first_avg = sum(first_half) / max(len(first_half), 1)
        second_avg = sum(second_half) / max(len(second_half), 1)
        if second_avg > first_avg * 1.12:
            insights.append(("趋势", "近段收入呈上升趋势，可适当提高高需求房型报价。"))
        elif second_avg < first_avg * 0.88:
            insights.append(("趋势", "近段收入有回落迹象，建议检查渠道转化和预抵订单。"))
        else:
            insights.append(("趋势", "近段收入整体平稳，建议保持当前价格策略。"))
    else:
        insights.append(("趋势", "收入样本较少，建议先补齐连续日期数据再判断趋势。"))

    occupancy = float(metrics.get("occupancy", 0) or 0)
    adr = float(metrics.get("adr", 0) or 0)
    if occupancy >= 75:
        insights.append(("出租率", "出租率较高，优先保障退房清洁和可售房释放。"))
    elif occupancy <= 35:
        insights.append(("出租率", "出租率偏低，可考虑会员定向促销或低峰特价。"))
    else:
        insights.append(("出租率", "出租率处于中间区间，重点关注房型结构和客源质量。"))

    if room_revenue:
        top_room, top_value = max(room_revenue.items(), key=lambda item: item[1])
        insights.append(("房型", f"{top_room}贡献最高（¥{top_value:.0f}），可优先保障该房型库存。"))

    order_count = int(metrics.get("order_count", 0) or 0)
    revenue = float(metrics.get("revenue", 0) or 0)
    if order_count and adr:
        insights.append(("建议", f"本期 {order_count} 单、收入 ¥{revenue:.0f}，建议复盘高价订单来源并沉淀会员偏好。"))

    return insights[:4]
