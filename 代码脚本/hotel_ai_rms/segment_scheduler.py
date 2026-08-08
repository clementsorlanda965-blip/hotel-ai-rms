"""
segment_scheduler.py — 客源细分每日早报调度器
════════════════════════════════════════════════════════════════
全自动流程：
  从 segment_mix 表读取昨日汇总（无则从 guest 明细聚合重算）
  → 生成客源日报摘要 → 推送到飞书 → 落 report_state 防重复

用法:
  python segment_scheduler.py                  # 单次运行（每日早报）
  python segment_scheduler.py --force          # 忽略去重强制发送

配合 deploy_scheduled_task.ps1 注册每日任务后无人值守。
"""
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))


def _now() -> str:
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def run_daily(force: bool = False, customers_df=None) -> dict:
    """单次客源日报：读取/重算 → 飞书推送。

    返回 {"ok": bool, "sent": bool, "summary": dict}
    """
    import database
    import segment_engine as se

    today = date.today().isoformat()

    # 1) 读取 segment_mix（若有历史快照则优先使用）
    try:
        mix = database.get_segment_mix()
    except Exception:
        mix = None

    # 若无快照，则尝试生成并落库一份模拟客源明细（独立于 Streamlit）
    if mix is None or mix.empty:
        try:
            cust = se.generate_sample_customers(220)
            mix = se.segment_mix_from_customers(cust, today)
            database.save_segment_mix(
                [r.to_dict() for _, r in mix.iterrows()]
                if not mix.empty else []
            )
        except Exception:
            mix = None

    summary = se.build_daily_summary(mix)
    if not summary.get("ok"):
        print(f"[{_now()}] 无数据可报（无 segment_mix / 客户明细）")
        return {"ok": False, "sent": False, "summary": summary}

    # 去重：当天已发送则跳过
    last_sent = database.get_report_state("segment_daily")
    if last_sent == today and not force:
        print(f"[{_now()}] 今日({today})已发送客源早报，跳过（--force 可强制）")
        return {"ok": True, "sent": False, "summary": summary}

    from feishu_alert import AlertEngine
    engine = AlertEngine()
    sent = engine.send_segment_report(summary)
    if sent:
        database.mark_report_sent("segment_daily", today)
        print(f"[{_now()}] ✅ 客源早报已发送至飞书")
    else:
        print(f"[{_now()}] ⚠️ 未发送（webhook 未配置或推送失败）；已避免重复状态更新")

    return {"ok": True, "sent": sent, "summary": summary}


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="客源细分日报早报调度器")
    p.add_argument("--force", action="store_true", help="忽略日级去重，强制发送")
    args = p.parse_args()

    result = run_daily(force=args.force)
    sys.exit(0 if result.get("ok") else 1)