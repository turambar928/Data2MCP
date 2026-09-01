"""
Chart Generation Agent - 自动生成趋势图、对比图
"""
import io
import logging
import os
from typing import Any, Dict, List, Optional
import base64

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # 使用非交互式后端
import matplotlib.pyplot as plt
import seaborn as sns

logger = logging.getLogger(__name__)

# 设置中文字体支持
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False


class ChartGenerationAgent:
    """
    图表生成Agent，提供以下功能：
    1. 生成趋势图 (line chart)
    2. 生成对比图 (bar chart)
    3. 生成散点图 (scatter plot)
    4. 生成热力图 (heatmap)
    """

    def __init__(self, output_dir: str = None):
        self.name = "chart_generation_agent"
        # 默认使用项目目录下的 output/charts
        if output_dir is None:
            # 获取项目根目录（从当前文件向上4级）
            current_file = os.path.abspath(__file__)
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_file)))))
            output_dir = os.path.join(project_root, "output", "charts")

        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"Chart output directory: {output_dir}")

    def generate_chart(
        self,
        data: Any,
        chart_type: str = "line",
        title: str = "Chart",
        x_label: str = "X",
        y_label: str = "Y",
        filename: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        生成图表

        Args:
            data: 输入数据
            chart_type: 图表类型 ("line", "bar", "scatter", "heatmap")
            title: 图表标题
            x_label: X轴标签
            y_label: Y轴标签
            filename: 输出文件名（不含路径）

        Returns:
            包含图表路径和markdown引用的字典
        """
        try:
            # 转换为DataFrame
            df = self._to_dataframe(data)

            if df is None or df.empty:
                return {"error": "No valid data to generate chart"}

            # 生成文件名
            if filename is None:
                filename = f"{chart_type}_{title.replace(' ', '_')}.png"

            filepath = os.path.join(self.output_dir, filename)

            # 根据图表类型生成图表
            if chart_type == "line":
                self._generate_line_chart(df, title, x_label, y_label, filepath)
            elif chart_type == "bar":
                self._generate_bar_chart(df, title, x_label, y_label, filepath)
            elif chart_type == "scatter":
                self._generate_scatter_chart(df, title, x_label, y_label, filepath)
            elif chart_type == "heatmap":
                self._generate_heatmap(df, title, filepath)
            else:
                return {"error": f"Unknown chart type: {chart_type}"}

            # 返回结果
            return {
                "success": True,
                "filepath": filepath,
                "filename": filename,
                "markdown": f"![{title}](/charts/{filename})",
            }

        except Exception as e:
            logger.error(f"Error generating chart: {e}")
            return {"error": str(e)}

    def generate_multiple_charts(
        self,
        data: Any,
        chart_configs: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        批量生成多个图表

        Args:
            data: 输入数据
            chart_configs: 图表配置列表，每个配置包含 chart_type, title, etc.

        Returns:
            图表结果列表
        """
        results = []
        for config in chart_configs:
            result = self.generate_chart(data, **config)
            results.append(result)
        return results

    def _to_dataframe(self, data: Any) -> Optional[pd.DataFrame]:
        """将输入数据转换为DataFrame"""
        try:
            if isinstance(data, pd.DataFrame):
                return data
            elif isinstance(data, dict):
                return pd.DataFrame(data)
            elif isinstance(data, list):
                return pd.DataFrame(data)
            else:
                return None
        except Exception as e:
            logger.error(f"Error converting to DataFrame: {e}")
            return None

    def _generate_line_chart(
        self,
        df: pd.DataFrame,
        title: str,
        x_label: str,
        y_label: str,
        filepath: str,
    ):
        """生成折线图"""
        plt.figure(figsize=(10, 6))

        # 绘制所有数值列
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            plt.plot(df.index, df[col], marker='o', label=col)

        plt.title(title, fontsize=14, fontweight='bold')
        plt.xlabel(x_label, fontsize=12)
        plt.ylabel(y_label, fontsize=12)
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()

    def _generate_bar_chart(
        self,
        df: pd.DataFrame,
        title: str,
        x_label: str,
        y_label: str,
        filepath: str,
    ):
        """生成柱状图"""
        plt.figure(figsize=(10, 6))

        # 如果有多列，使用分组柱状图
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 1:
            df[numeric_cols].plot(kind='bar', ax=plt.gca())
        else:
            plt.bar(df.index, df[numeric_cols[0]])

        plt.title(title, fontsize=14, fontweight='bold')
        plt.xlabel(x_label, fontsize=12)
        plt.ylabel(y_label, fontsize=12)
        plt.legend()
        plt.xticks(rotation=45, ha='right')
        plt.grid(True, alpha=0.3, axis='y')
        plt.tight_layout()
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()

    def _generate_scatter_chart(
        self,
        df: pd.DataFrame,
        title: str,
        x_label: str,
        y_label: str,
        filepath: str,
    ):
        """生成散点图"""
        plt.figure(figsize=(10, 6))

        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) >= 2:
            plt.scatter(df[numeric_cols[0]], df[numeric_cols[1]], alpha=0.6)
            plt.xlabel(numeric_cols[0], fontsize=12)
            plt.ylabel(numeric_cols[1], fontsize=12)
        else:
            plt.scatter(df.index, df[numeric_cols[0]], alpha=0.6)
            plt.xlabel(x_label, fontsize=12)
            plt.ylabel(numeric_cols[0], fontsize=12)

        plt.title(title, fontsize=14, fontweight='bold')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()

    def _generate_heatmap(
        self,
        df: pd.DataFrame,
        title: str,
        filepath: str,
    ):
        """生成热力图"""
        plt.figure(figsize=(10, 8))

        # 只使用数值列
        numeric_df = df.select_dtypes(include=[np.number])

        # 计算相关性矩阵
        if len(numeric_df.columns) > 1:
            corr = numeric_df.corr()
            sns.heatmap(corr, annot=True, cmap='coolwarm', center=0, fmt='.2f')
        else:
            # 如果只有一列，显示数据本身
            sns.heatmap(numeric_df.T, annot=True, cmap='YlOrRd', fmt='.2f')

        plt.title(title, fontsize=14, fontweight='bold')
        plt.tight_layout()
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()

    def format_chart_results(self, results: List[Dict[str, Any]]) -> str:
        """
        将图表结果格式化为markdown文本
        """
        output = []
        output.append("## Generated Charts\n")

        for i, result in enumerate(results, 1):
            if "error" in result:
                output.append(f"{i}. Error: {result['error']}")
            else:
                output.append(f"{i}. {result['markdown']}")

        return "\n".join(output)


# 创建全局实例
chart_agent = ChartGenerationAgent()
