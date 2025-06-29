# app.py

import sys
import os
import uuid
import json
import datetime
import re
from flask import Flask, render_template, request, stream_with_context, Response, send_from_directory, jsonify
from openai import OpenAI, AuthenticationError, APIConnectionError
from talk_to_data_core import TalkToDataCore
from evaluator import Evaluator
import tools

app = Flask(__name__)

if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    BASE_DIR = sys._MEIPASS
    SESSIONS_FOLDER = os.path.join(os.path.dirname(sys.executable), 'sessions')
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    SESSIONS_FOLDER = os.path.join(BASE_DIR, 'sessions')
os.makedirs(SESSIONS_FOLDER, exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/test_connection', methods=['POST'])
def test_connection():
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
    api_key = request.form.get('api_key')
    base_url = request.form.get('api_base_url')
    model_name = request.form.get('model_name')
    if not all([api_key, base_url, model_name]):
        return Response('{"error": "模型设置不完整"}', status=400, mimetype='application/json')

    session_id = f"talk-to-data-{uuid.uuid4()}"
    session_path = os.path.join(SESSIONS_FOLDER, session_id)
    plot_path = os.path.join(session_path, 'plots')
    upload_path = os.path.join(session_path, 'uploads')
    os.makedirs(plot_path, exist_ok=True)
    os.makedirs(upload_path, exist_ok=True)

    task = request.form.get('task')
    files = request.files.getlist('file')
    if not files or not any(f.filename for f in files) or not task:
        return Response('{"error": "必须提供任务和至少一个文件"}', status=400, mimetype='application/json')
    
    saved_files_paths = []
    for file in files:
        if file and file.filename:
            filepath = os.path.join(upload_path, file.filename)
            file.save(filepath)
            saved_files_paths.append(filepath)

    try:
        agent_core = TalkToDataCore(
            api_key=api_key,
            base_url=base_url,
            model_name=model_name,
            plot_save_dir=plot_path
        )
        # --- (核心修改) ---
        # 在创建 Evaluator 实例时，把 model_name 也传进去
        evaluator = Evaluator(
            api_key=api_key,
            base_url=base_url,
            model_name=model_name 
        )
    except Exception as e:
         return Response(f'{{"error": "初始化核心组件失败: {e}"}}', status=500, mimetype='application/json')
    
    def generate_stream():
        load_messages = []
        files_to_process = [
            p for p in saved_files_paths 
            if not p.lower().endswith(('.dbf', '.shx', '.prj', '.cpg', '.sbn', '.sbx'))
        ]
        for filepath in files_to_process:
            message = agent_core.load_data_from_filepath(filepath)
            if "已跳过加载" not in message:
                load_messages.append(message)
        
        initial_observation = "\n\n".join(load_messages)
        yield f"data: {json.dumps({'type': 'system', 'content': initial_observation})}\n\n"
        
        if "出错" in initial_observation or "失败" in initial_observation:
            return

        loaded_filenames = [os.path.basename(p) for p in files_to_process]
        full_task_description = f"数据已从以下文件加载: {loaded_filenames}。\n用户任务: {task}"
        
        session_history = []
        for step in agent_core.run(full_task_description):
            if step.get('type') != 'progress':
                session_history.append(step)
            
            if step.get('type') == 'observation' and '图表已生成并保存于:' in str(step.get('content', '')):
                server_path = step['content'].split(":", 1)[1].strip()
                web_path = os.path.join('sessions', session_id, 'plots', os.path.basename(server_path)).replace('\\', '/')
                step['content'] = f"图表已生成并保存于: {web_path}"
            
            yield f"data: {json.dumps(step)}\n\n"

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
    directory = os.path.join(SESSIONS_FOLDER, session_id, 'plots')
    return send_from_directory(directory, filename)

@app.route('/export_markdown', methods=['POST'])
def export_markdown():
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
    app.run(host='127.0.0.1', port=5001, debug=False)