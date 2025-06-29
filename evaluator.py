# evaluator.py

import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os
import uuid
from openai import OpenAI

plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

class Evaluator:
    def __init__(self, api_key, base_url, model_name):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model_name

    def generate_performance_chart(self, history, save_path):
        steps = []
        progress_scores = []
        turn = 0
        for message in history:
            if message.get('type') == 'action':
                turn += 1
                progress = min(100, turn * 10) 
                steps.append(f"第{turn}轮")
                progress_scores.append(progress)
        if not steps:
            return None
        plt.figure(figsize=(8, 5))
        plt.plot(steps, progress_scores, marker='o', linestyle='-')
        plt.title('Talk to Data 任务进度')
        plt.xlabel('思考/行动轮次')
        plt.ylabel('预估任务完成度 (%)')
        plt.grid(True)
        plt.ylim(0, 110)
        plt.savefig(save_path)
        plt.close()
        return save_path

    def evaluate_completion(self, task, final_summary, history, generated_plots):
        eval_prompt = f"""
请扮演一位数据分析专家的角色，评估AI助手 Talk to Data 的工作表现。

**原始任务**: {task}
**AI的最终总结**: {final_summary}
**AI生成的图表**: {generated_plots or '无'}

**评估标准**:
1.  **任务完成度**: 是否完整地回答了用户的所有问题？
2.  **准确性**: 分析结果和结论是否准确无误？
3.  **洞察力**: 是否发现了数据中潜在的有价值的信息？
4.  **效率**: 是否以最少的步骤完成任务？
5.  **可视化质量**: 图表是否清晰、信息丰富？

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