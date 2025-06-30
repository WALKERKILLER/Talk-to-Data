# talk_to_data_core.py

import json
import re
import os
import pandas as pd
from openai import OpenAI
from tools import ToolManager

try:
    import geopandas as gpd
except ImportError:
    gpd = None

class TalkToDataCore:

    def __init__(self, api_key, base_url, model_name, plot_save_dir, session_state):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model_name
        self.tool_manager = ToolManager(
            plot_save_dir=plot_save_dir, 
            session_state=session_state
        )
        self.system_prompt_content = self._construct_system_prompt()

    def _sanitize_filename_for_df_name(self, filename: str) -> str:
        base_name = os.path.splitext(filename)[0]
        sanitized = re.sub(r'\W|^(?=\d)', '_', base_name)
        return f"df_{sanitized}"

    def load_data_from_filepath(self, filepath: str) -> str:
        filename = os.path.basename(filepath)
        df_name = self._sanitize_filename_for_df_name(filename)
        try:
            if filepath.lower().endswith('.csv'):
                df = pd.read_csv(filepath)
            elif filepath.lower().endswith(('.xlsx', '.xls')):
                df = pd.read_excel(filepath)
            elif filepath.lower().endswith('.json'):
                try:
                    df = pd.read_json(filepath, orient='records')
                except ValueError:
                    df = pd.read_json(filepath)
            elif filepath.lower().endswith('.shp'):
                if gpd is None:
                    return "错误: 需要 'geopandas' 库来加载 .shp 文件。请运行 'pip install geopandas'。"
                df = gpd.read_file(filepath)
            else:
                return f"文件 '{filename}' 是一个辅助文件或不支持的格式，已跳过加载。"
            self.tool_manager.state["dataframes"][df_name] = df
            
            # --- 修改：为前端生成HTML表格 ---
            try:
                # to_html 会为前端生成一个美观的表格
                df_head_html = df.head().to_html(classes='data-table', border=0, index=False)
            except Exception:
                # 如果生成HTML失败，回退到纯文本
                df_head_html = f"<pre>{df.head().to_string(index=False)}</pre>"

            return (
                f"<p>文件 '{filename}' 已成功加载为 DataFrame '{df_name}'。</p>"
                f"<strong>数据预览：</strong>"
                f"<div class='table-wrapper'>{df_head_html}</div>"
            )
            # ---------------------------

        except Exception as e:
            return f"<p>加载文件 '{filename}' 时发生严重错误: {e}</p>"

    def _construct_system_prompt(self):
        tool_definitions = self.tool_manager.get_tool_definitions()
        return f"""
你是一个名为 Talk to Data 的AI数据分析助手。你的任务是根据用户的请求，通过思考和调用工具来一步步完成数据分析任务。
你现在可以处理一个或多个数据集。每个加载的数据文件都会被分配一个以 'df_' 开头的 DataFrame 名称。
你的工作流程严格遵循 "思考-行动-观察" (Thought-Action-Observation) 的模式：
1.  **思考 (Thought)**: 在 `<thought>` 标签中分析当前情况，明确你的目标，并规划下一步需要做什么。**如果存在多个 DataFrame，你应该首先使用 `list_dataframes` 工具来了解它们各自的结构。**
2.  **行动 (Action)**: 根据你的思考，在 `<action>` 标签中以严格的 JSON 格式选择一个最合适的工具来执行。JSON 格式必须为: `{{"tool": "tool_name", "args": {{...}}}}`
3.  你将得到一个 **观察 (Observation)** 结果，这是工具执行的输出。
重复以上步骤，直到当前子任务完成。当一个阶段的分析完成后，使用 `finish_task` 工具来提交你的阶段性结论和总结。用户可能会根据你的总结提出新的问题。
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
            return thought, {"error": "解析失败：在模型响应中未找到有效的 <action> 标签。"}
        try:
            action_str = re.sub(r'^```json\s*|\s*```$', '', action_str, flags=re.MULTILINE).strip()
            action = json.loads(action_str)
            return thought, action
        except json.JSONDecodeError:
            last_brace = action_str.rfind('}')
            if last_brace != -1:
                action_str_cleaned = action_str[:last_brace+1]
                try:
                    action = json.loads(action_str_cleaned)
                    return thought, action
                except json.JSONDecodeError:
                    pass
            return thought, {"error": f"行动指令不是一个有效的JSON格式。收到的内容: {action_str}"}

    def run(self, task: str, llm_history: list):
        if not any(msg['role'] == 'system' for msg in llm_history):
            llm_history.insert(0, {"role": "system", "content": self.system_prompt_content})
        
        # --- 修改：为LLM提供纯文本的数据加载信息 ---
        initial_user_content = f"任务: {task}"
        df_summaries = []
        for name, df in self.tool_manager.state.get("dataframes", {}).items():
            df_summaries.append(f"DataFrame '{name}' 的列为: {list(df.columns)}")
        if df_summaries:
            initial_user_content = "已加载以下数据:\n" + "\n".join(df_summaries) + f"\n\n用户的初始任务是: {task}"

        llm_history.append({"role": "user", "content": initial_user_content})
        # -----------------------------------
        
        max_turns = 25
        for i in range(max_turns):
            yield {"type": "progress", "value": (i / max_turns) * 100, "step": i + 1, "total_steps": max_turns}
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=llm_history,
                    temperature=0.1,
                )
                llm_output = response.choices[0].message.content
            except Exception as e:
                yield {"type": "observation", "content": f"调用LLM API时出错: {e}"}
                llm_history.pop() 
                break
            
            thought, action = self._parse_response(llm_output)

            if thought:
                yield {"type": "thought", "content": thought}
            
            llm_history.append({"role": "assistant", "content": llm_output})

            if action.get("error"):
                observation = f"解析错误: {action.get('error')}"
            else:
                tool_name = action.get("tool")
                if not tool_name:
                    observation = "解析错误：模型输出的JSON中缺少 'tool' 字段。"
                else:
                    if 'args' in action and isinstance(action.get('args'), dict):
                        tool_args = action['args']
                    else:
                        tool_args = {k: v for k, v in action.items() if k != 'tool'}
                    
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
                break
            
            # --- 修改：LLM的观察结果应该是纯文本，以避免上下文过大或解析问题 ---
            # 如果观察结果是HTML表格，我们只传递一个简短的确认信息给LLM
            if isinstance(observation, str) and observation.strip().startswith('<div class="table-wrapper">'):
                 observation_for_llm = "表格已生成并显示给用户。"
            else:
                 observation_for_llm = str(observation)
            llm_history.append({"role": "user", "content": f"观察结果:\n{observation_for_llm}"})
            # -------------------------------------------------------------------

        else:
            yield {"type": "final_summary", "content": "任务已达到最大步数限制，未能完成。"}