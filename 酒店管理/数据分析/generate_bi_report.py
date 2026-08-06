"""
generate_bi_report.py — 独立BI报表生成器
从数据库读取经营数据，一键生成专业Excel报表
用法:
    python generate_bi_report.py                      # 默认月度报告
    python generate_bi_report.py --type gop           # GOP深度分析
    python generate_bi_report.py --days 90 --hotel "九寨沟XX酒店"
    python generate_bi_report.py --type channel       # 渠道分析
    python generate_bi_report.py --type budget --occ 70 --adr 500 --revpar 350
"""
import sys
from pathlib import Path

# 确保能导入 hotel_ai_rms 目录的模块
RMS_DIR = Path(r"E:\工作AI\代码脚本\hotel_ai_rms")
if str(RMS_DIR) not in sys.path:
    sys.path.insert(0, str(RMS_DIR))

from datetime import date, timedelta
from database import get_latest_metrics, init_db
from bi_reports import (
    generate_sample_data, generate_excel_report,
    gop_deep_dive, generate_channel_analysis,
    load_from_database,
)
from data_import import seed_sample_data


def main():
    import argparse
    p = argparse.ArgumentParser(description="Hotel BI Report Generator")
    p.add_argument("--type", default="monthly",
                   choices=["monthly", "weekly", "gop", "channel", "budget"],
                   help="报表类型")
    p.add_argument("--days", type=int, default=30, help="数据天数")
    p.add_argument("--hotel", default="我的酒店", help="酒店名称")
    p.add_argument("--output", default="", help="输出路径（默认自动生成）")
    p.add_argument("--seed", action="store_true", help="先生成示例数据再出报表")
    # 预算参数
    p.add_argument("--occ", type=float, default=70, help="目标OCC")
    p.add_argument("--adr", type=float, default=500, help="目标ADR")
    p.add_argument("--revpar", type=float, default=350, help="目标RevPAR")
    p.add_argument("--revenue", type=float, default=500000, help="目标收入")
    p.add_argument("--gop_rate", type=float, default=35, help="目标GOP率")

    args = p.parse_args()

    init_db()

    # 种子数据
    if args.seed:
        n = seed_sample_data(max(args.days, 90))
        print(f"已生成 {n} 天示例数据")

    # 优先从数据库加载
    df = load_from_database(
        (date.today() - timedelta(days=args.days)).strftime("%Y-%m-%d"),
        date.today().strftime("%Y-%m-%d"),
    )
    if df is None or df.empty:
        print("数据库中无数据，使用模拟数据。")
        df = generate_sample_data(days=args.days)

    output_path = args.output if args.output else None

    if args.type == "gop":
        path = gop_deep_dive(df, hotel_name=args.hotel, output_path=output_path)
    elif args.type == "channel":
        channel_df = generate_channel_analysis()
        path = generate_excel_report(
            df, report_type="渠道分析", hotel_name=args.hotel,
            channel_df=channel_df, output_path=output_path,
        )
    elif args.type == "budget":
        budget = {
            "occ": args.occ, "adr": args.adr, "revpar": args.revpar,
            "revenue": args.revenue, "gop_rate": args.gop_rate,
        }
        path = generate_excel_report(
            df, report_type="预算执行分析", hotel_name=args.hotel,
            budget_targets=budget, output_path=output_path,
        )
    elif args.type == "weekly":
        path = generate_excel_report(
            df, report_type="周经营分析", hotel_name=args.hotel,
            output_path=output_path,
        )
    else:
        path = generate_excel_report(
            df, report_type="月度经营报告", hotel_name=args.hotel,
            output_path=output_path,
        )

    print(f"✅ 报表已生成：{path}")
    return path


if __name__ == "__main__":
    main()
