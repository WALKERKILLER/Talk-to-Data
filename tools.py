# tools.py
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import io
import uuid
import os
from contextlib import redirect_stdout

# --- 状态化内存 ---
STATE = {}

def reset_state():
    """重置全局状态，为新任务做准备。"""
    global STATE
    STATE = { "dataframes": {}, "plots": [] }

# --- 中文字体配置 ---
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

class ToolManager:
    def __init__(self, plot_save_dir):
        self.plot_save_dir = plot_save_dir
        self.state = STATE
        self._tools = {
            "run_python_code": self.run_python_code,
            "generate_plot": self.generate_plot,
            "list_dataframes": self.list_dataframes,
            "describe_data": self.describe_data,
            "correlation_analysis": self.correlation_analysis,
            "handle_missing_values": self.handle_missing_values,
            "train_linear_regression": self.train_linear_regression,
            "finish_task": self.finish_task,
        }

    def get_tool_definitions(self):
        """供 LLM 理解的工具定义"""
        # --- 关键修正：现在不再需要 save_path 占位符了 ---
        return [
            {"name": "run_python_code", "description": "执行Python代码来操作`dataframes`字典中的数据。例如: `print(dataframes['initial_data'].head())`", "parameters": {"type": "object", "properties": {"code": {"type": "string"}}, "required": ["code"]}},
            {"name": "generate_plot", "description": "执行Python代码生成图表。代码中必须包含`plt.savefig(save_path)`。一个名为 `save_path` 的变量会自动提供给你，你必须直接使用它。", "parameters": {"type": "object", "properties": {"code": {"type": "string"}}, "required": ["code"]}},
            {"name": "list_dataframes", "description": "列出内存中所有DataFrame的名称及其信息。", "parameters": {}},
            {"name": "describe_data", "description": "生成DataFrame的描述性统计信息。", "parameters": {"type": "object", "properties": {"df_name": {"type": "string"}}, "required": ["df_name"]}},
            {"name": "correlation_analysis", "description": "计算DataFrame中数值列的相关系数矩阵。", "parameters": {"type": "object", "properties": {"df_name": {"type": "string"}}, "required": ["df_name"]}},
            {"name": "handle_missing_values", "description": "处理DataFrame中的缺失值。", "parameters": {"type": "object", "properties": {"df_name": {"type": "string"}, "method": {"type": "string", "enum": ["fill_mean", "fill_median", "fill_mode", "drop"]}}, "required": ["df_name", "method"]}},
            {"name": "train_linear_regression", "description": "训练一个简单的线性回归模型。", "parameters": {"type": "object", "properties": {"df_name": {"type": "string"}, "target_column": {"type": "string"}, "feature_columns": {"type": "array", "items": {"type": "string"}}}, "required": ["df_name", "target_column", "feature_columns"]}},
            {"name": "finish_task", "description": "所有分析任务完成时调用此工具，提交最终总结。", "parameters": {"type": "object", "properties": {"summary": {"type": "string"}}, "required": ["summary"]}},
        ]

    def dispatch(self, tool_name, **kwargs):
        if tool_name not in self._tools: return f"错误：未知的工具 '{tool_name}'"
        try: return self._tools[tool_name](**kwargs)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return f"错误：执行工具 '{tool_name}' 时发生异常: {e}"

    def run_python_code(self, code: str):
        f = io.StringIO()
        with redirect_stdout(f):
            try:
                exec_globals = { "dataframes": self.state["dataframes"], "pd": pd, "np": np }
                exec_globals.update(self.state["dataframes"])
                exec(code, exec_globals)
            except Exception as e: return f"代码执行错误: [{type(e).__name__}] {e}"
        return f"代码执行成功。\n输出:\n{f.getvalue()}"

    def generate_plot(self, code: str):
        plot_filename = f"{uuid.uuid4()}.png"
        
        # self.plot_save_dir 是从 app.py 传来的绝对路径
        save_path = os.path.join(self.plot_save_dir, plot_filename)
        
        # --- 直接将 save_path 变量注入 exec 环境 ---
        # 不再使用 .format()，从根本上杜绝路径字符串转义问题。
        # LLM 生成的代码现在应该是 `plt.savefig(save_path)`
        
        try:
            # 准备执行环境
            exec_globals = {
                "dataframes": self.state["dataframes"],
                "plt": plt,
                "pd": pd,
                "np": np,
                "save_path": save_path  # <-- 核心修复！直接注入路径变量
            }
            exec_globals.update(self.state["dataframes"])

            # 直接执行代码，无需切换工作目录
            exec(code, exec_globals)

        except Exception as e:
            import traceback
            traceback.print_exc()
            return f"绘图代码执行错误: [{type(e).__name__}] {e}"

        if os.path.exists(save_path):
            self.state["plots"].append(save_path)
            return f"图表已生成并保存于: {save_path}"
        else:
            return f"错误: 绘图代码已执行，但未在预期路径 '{save_path}' 找到图表文件。请确保代码中调用了 `plt.savefig(save_path)`。"


    def list_dataframes(self):
        if not self.state["dataframes"]: return "当前内存中没有DataFrame。"
        infos = []
        for name, df in self.state["dataframes"].items():
            buffer = io.StringIO()
            df.info(buf=buffer)
            infos.append(f"--- DataFrame: {name} ---\n{buffer.getvalue()}")
        return "\n".join(infos)

    def describe_data(self, df_name: str):
        if df_name not in self.state["dataframes"]: return f"错误: 找不到DataFrame '{df_name}'"
        return f"'{df_name}' 的描述性统计:\n{self.state['dataframes'][df_name].describe().to_string()}"

    def correlation_analysis(self, df_name: str):
        if df_name not in self.state["dataframes"]: return f"错误: 找不到DataFrame '{df_name}'"
        df = self.state["dataframes"][df_name].select_dtypes(include=np.number)
        if df.empty: return "错误: DataFrame中没有数值列可进行相关性分析。"
        return f"'{df_name}' 的相关系数矩阵:\n{df.corr().to_string()}"

    def handle_missing_values(self, df_name: str, method: str):
        if df_name not in self.state["dataframes"]: return f"错误: 找不到DataFrame '{df_name}'"
        df = self.state["dataframes"][df_name]
        original_rows = len(df)
        if method == "fill_mean":
            df.fillna(df.select_dtypes(include=np.number).mean(), inplace=True)
            return f"已使用均值填充 '{df_name}' 的缺失值。"
        elif method == "fill_median":
            df.fillna(df.select_dtypes(include=np.number).median(), inplace=True)
            return f"已使用中位数填充 '{df_name}' 的缺失值。"
        elif method == "fill_mode":
            for col in df.columns: df[col].fillna(df[col].mode()[0], inplace=True)
            return f"已使用众数填充 '{df_name}' 中的缺失值。"
        elif method == "drop":
            df.dropna(inplace=True)
            return f"已删除 '{df_name}' 中包含缺失值的 {original_rows - len(df)} 行。"
        return f"错误: 未知的处理方法 '{method}'"

    def train_linear_regression(self, df_name: str, target_column: str, feature_columns: list):
        if df_name not in self.state["dataframes"]: return f"错误: 找不到DataFrame '{df_name}'"
        df = self.state["dataframes"][df_name]
        cols_to_check = [target_column] + feature_columns
        non_numeric_cols = df[cols_to_check].select_dtypes(exclude=np.number).columns
        if not non_numeric_cols.empty: return f"错误: 列 {list(non_numeric_cols)} 不是数值类型。"
        X = df[feature_columns].values
        y = df[target_column].values
        X = np.column_stack([np.ones(X.shape[0]), X])
        try:
            coeffs = np.linalg.inv(X.T @ X) @ X.T @ y
            return {"intercept": coeffs[0], "coefficients": dict(zip(feature_columns, coeffs[1:]))}
        except np.linalg.LinAlgError: return "训练模型时出错：无法计算系数，可能存在共线性。"

    def finish_task(self, summary: str):
        return {"summary": summary, "status": "finished"}