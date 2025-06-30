# evaluator.py

import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import os
import uuid
from openai import OpenAI

# 设置中文字体和负号显示
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

class Evaluator:
    def __init__(self, api_key, base_url, model_name):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model_name

    # --- START OF CHANGE: Reworked and styled the radar chart function ---
    def generate_evaluation_radar_chart(self, details, save_path):
        """
        生成一个设计精美的评估维度雷达图。
        :param details: 包含各维度评分的字典，例如 {"completeness": 8, "accuracy": 9, ...}
        :param save_path: 图表保存路径
        """
        if not details or not any(isinstance(v, (int, float)) and v > 0 for v in details.values()):
            return None # 如果没有有效的评分细节，则不生成图表

        labels_map = {
            "completeness": "任务完成度",
            "accuracy": "准确性",
            "insight": "洞察力",
            "efficiency": "效率",
            "visualization": "可视化质量"
        }
        
        # 保证顺序并过滤掉不存在的键
        labels = [labels_map[k] for k in labels_map if k in details]
        stats = [details.get(k, 0) for k in labels_map if k in details]

        if not labels:
            return None

        # 创建雷达图角度
        angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
        
        # 使图形闭合
        stats += stats[:1]
        angles += angles[:1]

        # --- 美学设计 ---
        fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
        
        # 1. 设置背景颜色为透明
        fig.patch.set_alpha(0)
        ax.patch.set_alpha(0)
        
        # 2. 绘制数据线和填充区域
        ax.plot(angles, stats, color='#00e676', linewidth=2, linestyle='solid', label='AI能力') # 明亮的绿色数据线
        ax.fill(angles, stats, color='#00e676', alpha=0.25) # 半透明填充
        
        # 3. 设置标签和刻度
        ax.set_yticklabels([]) # 隐藏默认的径向标签
        ax.set_thetagrids(np.degrees(angles[:-1]), labels, color='white', fontsize=12, weight='bold')

        # 4. 设置径向刻度和网格
        ax.set_rlabel_position(0)
        r_ticks = [2, 4, 6, 8, 10]
        ax.set_yticks(r_ticks)
        ax.set_ylim(0, 10.5) # 留出一点空间
        
        # 5. 自定义径向刻度标签，使其更柔和
        for tick in r_ticks:
             ax.text(np.pi / 2, tick + 0.2, str(tick), color="grey", size=10, ha="center", va="center")

        # 6. 设置网格线和最外圈的样式
        ax.spines['polar'].set_color('grey') # 改变最外圈的颜色
        ax.grid(color='grey', linestyle='--', linewidth=0.5)

        # 7. 添加标题
        plt.title('AI 能力评估雷达图', size=16, color='white', y=1.1, weight='bold')
        
        # 8. 保存高质量、背景透明的图片
        plt.savefig(save_path, dpi=150, transparent=True)
        plt.close()
        
        return save_path
    # --- END OF CHANGE ---

    def evaluate_completion(self, task, final_summary, history, generated_plots):
        eval_prompt = f"""
请扮演一位数据分析专家的角色，评估AI助手 Talk to Data 的工作表现。

**原始任务**: {task}
**AI的最终总结**: {final_summary}
**AI生成的图表**: {generated_plots or '无'}

**评估标准**:
1.  **任务完成度**: 是否完整地回答了用户的所有问题？ (1-10分)
2.  **准确性**: 分析结果和结论是否准确无误？ (1-10分)
3.  **洞察力**: 是否发现了数据中潜在的有价值的信息？ (1-10分)
4.  **效率**: 是否以最少的步骤完成任务？是否有不必要的重复或错误？ (1-10分)
5.  **可视化质量**: 图表是否清晰、信息丰富、美观？ (1-10分)

请根据以上标准，给出一个1-10分的总分，并提供详细的评语。

请以严格的 JSON 格式返回你的评估结果:
`{{
    "score": <总分>,
    "justification": "<综合评语>",
    "details": {{
        "completeness": <完成度评分>,
        "accuracy": <准确性评分>,
        "insight": <洞察力评分>,
        "efficiency": <效率评分>,
        "visualization": <可视化评分>
    }}
}}`
"""
        try:
            # 现在这里的 self.model 会使用用户指定的模型了
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": eval_prompt}],
                response_format={"type": "json_object"},
                temperature=0.1,
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            # 改进错误提示，让用户知道是评估环节出的问题
            error_message = f"调用评估模型时发生错误: {e}"
            return {
                "score": 0, "justification": error_message,
                "details": {"completeness": 0, "accuracy": 0, "insight": 0, "efficiency": 0, "visualization": 0},
                "error": str(e)
            }