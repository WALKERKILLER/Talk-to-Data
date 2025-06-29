# app.py

# --- 核心导入 ---
import sys
import os
import uuid
import json
import datetime
import re

# --- Web 和应用框架导入 ---
from flask import Flask, render_template, request, stream_with_context, Response, send_from_directory, jsonify

# --- 第三方库导入 ---
import pandas as pd
from openai import OpenAI, AuthenticationError, APIConnectionError

# --- 本地项目模块导入 ---
from talk_to_data_core import TalkToDataCore
from evaluator import Evaluator
import tools

# --- 应用初始化 ---
# 在 Electron 环境中，Flask 实例的创建方式保持不变
app = Flask(__name__)

# --- 路径管理：兼容开发环境和打包后的环境 ---
# 这是确保打包后应用能正确找到文件的关键
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    # 如果是 PyInstaller 打包后的单文件应用
    # sys._MEIPASS 是 PyInstaller 在运行时创建的临时文件夹的路径
    BASE_DIR = sys._MEIPASS
    # 对于 Electron Builder，它通常将 Python 脚本放在 resources 目录中
    # 一个更稳健的方式是依赖于可执行文件本身的位置
    SESSIONS_FOLDER = os.path.join(os.path.dirname(sys.executable), 'sessions')
else:
    # 如果是正常运行的 .py 脚本（开发环境）
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    SESSIONS_FOLDER = os.path.join(BASE_DIR, 'sessions')

# 确保会话目录存在
os.makedirs(SESSIONS_FOLDER, exist_ok=True)


# --- Flask 路由定义 ---

@app.route('/')
def index():
    """渲染主页面。"""
    return render_template('index.html')


@app.route('/test_connection', methods=['POST'])
def test_connection():
    """测试与大模型API的连接是否有效。"""
    data = request.json
    api_key = data.get('api_key')
    base_url = data.get('api_base_url')

    if not api_key or not base_url:
        return jsonify({"success": False, "message": "API Key 和地址不能为空"}), 400

    try:
        client = OpenAI(api_key=api_key, base_url=base_url, timeout=10.0)
        client.models.list()
        return jsonify({"success": True, "message": "连接成功！设置有效。"})
    except AuthenticationError:
        return jsonify({"success": False, "message": "连接失败：API Key 无效或不正确。"}), 401
    except APIConnectionError:
        return jsonify({"success": False, "message": "连接失败：无法连接到 API 地址。请检查 URL 或网络。"}), 400
    except Exception as e:
        return jsonify({"success": False, "message": f"发生未知错误: {e}"}), 500


@app.route('/run_analysis', methods=['POST'])
def run_analysis():
    """处理分析请求，为每次请求创建独立的会话和文件夹。"""
    
    # 1. 从前端请求中动态获取模型设置
    api_key = request.form.get('api_key')
    base_url = request.form.get('api_base_url')
    model_name = request.form.get('model_name')
    if not all([api_key, base_url, model_name]):
        return Response('{"error": "模型设置不完整"}', status=400, mimetype='application/json')

    # 2. 会话隔离
    session_id = f"talk-to-data-{uuid.uuid4()}"
    session_path = os.path.join(SESSIONS_FOLDER, session_id)
    plot_path = os.path.join(session_path, 'plots')
    upload_path = os.path.join(session_path, 'uploads')
    os.makedirs(plot_path, exist_ok=True)
    os.makedirs(upload_path, exist_ok=True)

    # 3. 文件校验
    task = request.form.get('task')
    file = request.files.get('file')
    if not file or not file.filename or not task:
        return Response('{"error": "必须提供任务和文件"}', status=400, mimetype='application/json')
    
    filepath = os.path.join(upload_path, file.filename)
    file.save(filepath)

    # 4. 实例化组件
    try:
        agent_core = TalkToDataCore(
            api_key=api_key,
            base_url=base_url,
            model_name=model_name,
            plot_save_dir=plot_path
        )
        evaluator = Evaluator(api_key=api_key, base_url=base_url)
    except Exception as e:
         return Response(f'{{"error": "初始化核心组件失败: {e}"}}', status=500, mimetype='application/json')
    
    def generate_stream():
        # 5. 加载数据
        initial_observation = agent_core.load_data_from_filepath(filepath)
        yield f"data: {json.dumps({'type': 'system', 'content': initial_observation})}\n\n"
        if "出错" in initial_observation or "失败" in initial_observation:
            return

        # 6. 运行 Agent
        full_task_description = f"数据已从 '{file.filename}' 加载到 'initial_data' DataFrame。\n用户任务: {task}"
        
        session_history = []
        for step in agent_core.run(full_task_description):
            if step.get('type') != 'progress':
                session_history.append(step)
            
            if step.get('type') == 'observation' and '图表已生成并保存于:' in str(step.get('content', '')):
                server_path = step['content'].split(":", 1)[1].strip()
                web_path = os.path.join('sessions', session_id, 'plots', os.path.basename(server_path)).replace('\\', '/')
                step['content'] = f"图表已生成并保存于: {web_path}"
            
            yield f"data: {json.dumps(step)}\n\n"

        # 7. 评估
        final_summary = "任务未正常结束。"
        for item in reversed(session_history):
            if item.get('type') == 'final_summary':
                final_summary = item['content']
                break
        
        web_plots = [
            os.path.join('sessions', session_id, 'plots', os.path.basename(p)).replace('\\', '/')
            for p in agent_core.tool_manager.state['plots']
        ]

        evaluation = evaluator.evaluate_completion(
            task=task,
            final_summary=final_summary,
            history=session_history,
            generated_plots=web_plots
        )
        
        eval_chart_save_path = os.path.join(plot_path, f"eval_chart_{uuid.uuid4()}.png")
        evaluator.generate_performance_chart(history=session_history, save_path=eval_chart_save_path)
        if os.path.exists(eval_chart_save_path):
            eval_chart_web_path = os.path.join('sessions', session_id, 'plots', os.path.basename(eval_chart_save_path)).replace('\\', '/')
            evaluation['chart_path'] = eval_chart_web_path
        else:
            evaluation['chart_path'] = None

        yield f"data: {json.dumps({'type': 'evaluation', 'content': evaluation})}\n\n"

    return Response(stream_with_context(generate_stream()), mimetype='text/event-stream')


@app.route('/sessions/<session_id>/plots/<filename>')
def serve_session_plot(session_id, filename):
    """这个路由使得形如 'sessions/id/plots/file.png' 的 URL 能够访问到服务器上的文件"""
    directory = os.path.join(SESSIONS_FOLDER, session_id, 'plots')
    return send_from_directory(directory, filename)


@app.route('/export_markdown', methods=['POST'])
def export_markdown():
    """将前端发来的会话历史数据生成 Markdown 文件并提供下载"""
    history_data = request.get_json()
    if not history_data:
        return Response('{"error": "没有提供历史数据"}', status=400, mimetype='application/json')
    
    markdown_content = []
    report_title = "Talk to Data 分析报告"
    export_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    markdown_content.append(f"# {report_title}\n\n**导出时间:** {export_time}\n\n---\n")

    for message in history_data:
        msg_type = message.get("type", "unknown").title()
        content = message.get("content", "")

        if msg_type == 'Action':
            tool_match = re.search(r'调用工具: ([\w_]+)', content)
            args_match = re.search(r'参数: (\{.*\})$', content, re.S)
            if tool_match and args_match:
                tool_name = tool_match.group(1)
                try:
                    args_dict = json.loads(args_match.group(1))
                    formatted_content = f"**工具**: `{tool_name}`\n\n**参数**:\n```json\n{json.dumps(args_dict, indent=2, ensure_ascii=False)}\n```"
                except json.JSONDecodeError:
                    formatted_content = f"```\n{content}\n```"
            else:
                 formatted_content = f"```\n{content}\n```"
            markdown_content.append(f"## ⚡️ {msg_type}\n\n{formatted_content}\n")
        elif msg_type in ['System', 'Thought', 'Final Summary', 'Observation', 'User Request']:
            icon_map = {'System': '⚙️', 'Thought': '🧠', 'Observation': '📊', 'Final Summary': '📝', 'User Request': '👤'}
            markdown_content.append(f"## {icon_map.get(msg_type, '💬')} {msg_type}\n\n")
            
            if 'sessions/' in str(content) and any(ext in str(content) for ext in ['.png', '.jpg', '.jpeg']):
                plot_web_path_match = re.search(r'(sessions/.*?\.png)', str(content))
                if plot_web_path_match:
                    plot_filename = os.path.basename(plot_web_path_match.group(1))
                    markdown_content.append(f"![生成的图表: {plot_filename}]({plot_filename})\n\n*(注意: 图片文件需要与本报告放在同一目录下才能显示)*\n")
                else:
                    markdown_content.append(f"```\n{str(content)}\n```\n")
            else:
                markdown_content.append(f"```\n{str(content)}\n```\n")

    full_markdown = "\n".join(markdown_content)
    filename = f"Talk_to_Data_Report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    
    return Response(
        full_markdown,
        mimetype="text/markdown",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )


if __name__ == '__main__':
    # 当这个脚本被直接执行时（例如通过 python app.py 或被 Electron 的子进程调用），
    # 它会启动 Flask 开发服务器。
    # debug=False 是推荐的，因为在 Electron 中，我们通过开发者工具来调试前端。
    # host='127.0.0.1' 确保服务只在本地可访问。
    app.run(host='127.0.0.1', port=5001, debug=False)