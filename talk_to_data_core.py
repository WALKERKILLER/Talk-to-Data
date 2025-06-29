# talk_to_data_core.py
import json
import re
import os
import pandas as pd
from openai import OpenAI
from tools import ToolManager, reset_state

class TalkToDataCore:
    def __init__(self, api_key, base_url, model_name, plot_save_dir):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model_name
        reset_state()
        self.tool_manager = ToolManager(plot_save_dir=plot_save_dir)

    def load_data_from_filepath(self, filepath: str, df_name: str = "initial_data") -> str:
        """
        从指定文件路径加载CSV数据到工具管理器的状态中。
        """
        try:
            df = pd.read_csv(filepath)
            self.tool_manager.state["dataframes"][df_name] = df
            df_head_info = df.head().to_markdown(index=False)
            return f"文件 '{os.path.basename(filepath)}' 已成功加载为 '{df_name}'。\n数据预览如下：\n\n{df_head_info}"
        except Exception as e:
            return f"加载CSV文件时出错: {e}"

    def _construct_system_prompt(self):
        tool_definitions = self.tool_manager.get_tool_definitions()
        return f"""
你是一个名为 Talk to Data 的AI数据分析助手。你的任务是根据用户的请求，通过思考和调用工具来一步步完成数据分析任务。

你的工作流程严格遵循 "思考-行动-观察" (Thought-Action-Observation) 的模式：

1.  **思考 (Thought)**: 在 `<thought>` 标签中分析当前情况，明确你的目标，并规划下一步需要做什么。
2.  **行动 (Action)**: 根据你的思考，在 `<action>` 标签中以严格的 JSON 格式选择一个最合适的工具来执行。JSON 格式必须为: `{{"tool": "tool_name", "args": {{...}}}}`
3.  你将得到一个 **观察 (Observation)** 结果，这是工具执行的输出。

重复以上步骤，直到任务完成。当所有分析都完成后，必须使用 `finish_task` 工具来提交你的最终结论和总结。

你可用的工具有:
{json.dumps(tool_definitions, indent=2, ensure_ascii=False)}

请务必严格遵循 `<thought>` 和 `<action>` 的输出格式，不要有任何多余的文字。
"""

    def _parse_response(self, llm_output: str):
        thought_match = re.search(r'<thought>(.*?)</thought>', llm_output, re.DOTALL)
        action_match = re.search(r'<action>(.*?)</action>', llm_output, re.DOTALL)
        
        thought = thought_match.group(1).strip() if thought_match else None
        action_str = action_match.group(1).strip() if action_match else None
        
        if not action_str:
            return thought, {"error": "未找到有效的 <action> 标签。"}

        try:
            action = json.loads(action_str)
            return thought, action
        except json.JSONDecodeError:
            return thought, {"error": "行动指令不是一个有效的JSON格式。"}

    def run(self, task: str):
        system_prompt = self._construct_system_prompt()
        history = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": task}
        ]
        
        max_turns = 15
        for i in range(max_turns):
            yield {"type": "progress", "value": (i / max_turns) * 100, "step": i + 1, "total_steps": max_turns}

            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=history,
                    temperature=0.1,
                )
                llm_output = response.choices[0].message.content
            except Exception as e:
                yield {"type": "observation", "content": f"调用LLM API时出错: {e}"}
                break

            thought, action = self._parse_response(llm_output)

            if thought:
                yield {"type": "thought", "content": thought}
            
            history.append({"role": "assistant", "content": llm_output})

            if action.get("error"):
                observation = f"解析错误: {action.get('error')}"
            else:
                tool_name = action.get("tool")
                tool_args = action.get("args", {})
                yield {"type": "action", "content": f"调用工具: {tool_name}，参数: {json.dumps(tool_args, ensure_ascii=False)}"}
                
                observation = self.tool_manager.dispatch(tool_name, **tool_args)

            try:
                json.dumps(observation)
            except (TypeError, OverflowError):
                observation = str(observation)

            yield {"type": "observation", "content": observation}

            if isinstance(observation, dict) and observation.get("status") == "finished":
                yield {"type": "progress", "value": 100, "step": i + 1, "total_steps": max_turns}
                yield {"type": "final_summary", "content": observation['summary']}
                return
            
            history.append({"role": "user", "content": f"观察结果:\n{str(observation)}"})
        
        yield {"type": "final_summary", "content": "任务已达到最大步数限制，未能完成。"}