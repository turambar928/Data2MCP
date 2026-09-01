"""
Data Analysis Agent - 自动计算增长率、市场份额、统计指标
"""
import json
import logging
from typing import Any, Dict, List, Optional

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class DataAnalysisAgent:
    """
    数据分析Agent，提供以下功能：
    1. 计算增长率 (growth rate)
    2. 计算市场份额 (market share)
    3. 计算统计指标 (mean, median, std, etc.)
    4. 生成结构化的分析结果
    """

    def __init__(self):
        self.name = "data_analysis_agent"

    def analyze_data(self, data: Any, analysis_type: str = "auto") -> Dict[str, Any]:
        """
        分析数据并返回结构化结果

        Args:
            data: 输入数据，可以是dict, list, 或pandas DataFrame
            analysis_type: 分析类型 ("auto", "growth", "share", "stats")

        Returns:
            包含分析结果的字典
        """
        try:
            # 转换为DataFrame
            df = self._to_dataframe(data)

            if df is None or df.empty:
                return {"error": "No valid data to analyze"}

            results = {
                "summary": self._generate_summary(df),
            }

            # 根据分析类型执行不同的分析
            if analysis_type in ["auto", "growth"]:
                results["growth_analysis"] = self._calculate_growth_rates(df)

            if analysis_type in ["auto", "share"]:
                results["market_share"] = self._calculate_market_share(df)

            if analysis_type in ["auto", "stats"]:
                results["statistics"] = self._calculate_statistics(df)

            return results

        except Exception as e:
            logger.error(f"Error in data analysis: {e}")
            return {"error": str(e)}

    def _to_dataframe(self, data: Any) -> Optional[pd.DataFrame]:
        """将输入数据转换为DataFrame"""
        try:
            if isinstance(data, pd.DataFrame):
                return data
            elif isinstance(data, dict):
                return pd.DataFrame(data)
            elif isinstance(data, list):
                return pd.DataFrame(data)
            elif isinstance(data, str):
                # 尝试解析JSON字符串
                try:
                    parsed = json.loads(data)
                    return pd.DataFrame(parsed)
                except:
                    return None
            else:
                return None
        except Exception as e:
            logger.error(f"Error converting to DataFrame: {e}")
            return None

    def _generate_summary(self, df: pd.DataFrame) -> Dict[str, Any]:
        """生成数据摘要"""
        return {
            "total_rows": len(df),
            "total_columns": len(df.columns),
            "columns": list(df.columns),
            "numeric_columns": list(df.select_dtypes(include=[np.number]).columns),
        }

    def _calculate_growth_rates(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        计算增长率

        对于数值列，计算：
        - 逐行增长率 (pct_change)
        - 总体增长率 (first to last)
        - 平均增长率
        """
        results = {}
        numeric_cols = df.select_dtypes(include=[np.number]).columns

        for col in numeric_cols:
            try:
                series = df[col].dropna()
                if len(series) < 2:
                    continue

                # 计算逐行增长率
                pct_change = series.pct_change().dropna()

                # 计算总体增长率
                first_value = series.iloc[0]
                last_value = series.iloc[-1]
                total_growth = ((last_value - first_value) / first_value * 100) if first_value != 0 else 0

                results[col] = {
                    "total_growth_rate": f"{total_growth:.1f}%",
                    "total_growth_value": f"{first_value:.2f} → {last_value:.2f}",
                    "average_growth_rate": f"{pct_change.mean() * 100:.1f}%",
                    "max_growth_rate": f"{pct_change.max() * 100:.1f}%",
                    "min_growth_rate": f"{pct_change.min() * 100:.1f}%",
                }
            except Exception as e:
                logger.warning(f"Error calculating growth for {col}: {e}")
                continue

        return results

    def _calculate_market_share(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        计算市场份额

        对于数值列，计算每个值占总和的百分比
        """
        results = {}
        numeric_cols = df.select_dtypes(include=[np.number]).columns

        for col in numeric_cols:
            try:
                series = df[col].dropna()
                if len(series) == 0:
                    continue

                total = series.sum()
                if total == 0:
                    continue

                # 计算市场份额
                shares = (series / total * 100).round(2)

                results[col] = {
                    "total": f"{total:.2f}",
                    "shares": shares.to_dict(),
                    "top_3": shares.nlargest(3).to_dict(),
                }
            except Exception as e:
                logger.warning(f"Error calculating market share for {col}: {e}")
                continue

        return results

    def _calculate_statistics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        计算统计指标

        包括：mean, median, std, min, max, quartiles
        """
        results = {}
        numeric_cols = df.select_dtypes(include=[np.number]).columns

        for col in numeric_cols:
            try:
                series = df[col].dropna()
                if len(series) == 0:
                    continue

                results[col] = {
                    "mean": f"{series.mean():.2f}",
                    "median": f"{series.median():.2f}",
                    "std": f"{series.std():.2f}",
                    "min": f"{series.min():.2f}",
                    "max": f"{series.max():.2f}",
                    "q25": f"{series.quantile(0.25):.2f}",
                    "q75": f"{series.quantile(0.75):.2f}",
                }
            except Exception as e:
                logger.warning(f"Error calculating statistics for {col}: {e}")
                continue

        return results

    def format_analysis_result(self, analysis_result: Dict[str, Any]) -> str:
        """
        将分析结果格式化为易读的文本
        """
        if "error" in analysis_result:
            return f"Analysis Error: {analysis_result['error']}"

        output = []

        # Summary
        if "summary" in analysis_result:
            summary = analysis_result["summary"]
            output.append("## Data Summary")
            output.append(f"- Total rows: {summary.get('total_rows', 0)}")
            output.append(f"- Total columns: {summary.get('total_columns', 0)}")
            output.append(f"- Numeric columns: {', '.join(summary.get('numeric_columns', []))}")
            output.append("")

        # Growth Analysis
        if "growth_analysis" in analysis_result:
            output.append("## Growth Rate Analysis")
            for col, data in analysis_result["growth_analysis"].items():
                output.append(f"\n**{col}**:")
                output.append(f"- Total growth: {data['total_growth_rate']} ({data['total_growth_value']})")
                output.append(f"- Average growth rate: {data['average_growth_rate']}")
                output.append(f"- Max growth rate: {data['max_growth_rate']}")
                output.append(f"- Min growth rate: {data['min_growth_rate']}")
            output.append("")

        # Market Share
        if "market_share" in analysis_result:
            output.append("## Market Share Analysis")
            for col, data in analysis_result["market_share"].items():
                output.append(f"\n**{col}** (Total: {data['total']}):")
                output.append("Top 3 market shares:")
                for key, value in data['top_3'].items():
                    output.append(f"  - {key}: {value}%")
            output.append("")

        # Statistics
        if "statistics" in analysis_result:
            output.append("## Statistical Summary")
            for col, data in analysis_result["statistics"].items():
                output.append(f"\n**{col}**:")
                output.append(f"- Mean: {data['mean']}, Median: {data['median']}, Std: {data['std']}")
                output.append(f"- Range: {data['min']} - {data['max']}")
                output.append(f"- Q25: {data['q25']}, Q75: {data['q75']}")
            output.append("")

        return "\n".join(output)


# 创建全局实例
analysis_agent = DataAnalysisAgent()
