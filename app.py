# app.py

import sys
import os
import uuid
import json
import datetime
import re
import shutil # <--- 1. 导入 shutil 库
from flask import Flask, render_template, request, stream_with_context, Response, send_from_directory, jsonify
from openai import OpenAI, AuthenticationError, APIConnectionError
from talk_to_data_core import TalkToDataCore
from evaluator import Evaluator

app = Flask(__name__)

if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    BASE_DIR = sys._MEIPASS
    SESSIONS_FOLDER = os.path.join(os.path.dirname(sys.executable), 'sessions')
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    SESSIONS_FOLDER = os.path.join(BASE_DIR, 'sessions')
os.makedirs(SESSIONS_FOLDER, exist_ok=True)


class SessionManager:
    def __init__(self):
        self.sessions = {}

    def create_session(self):
        session_id = f"talk-to-data-{uuid.uuid4()}"
        session_path = os.path.join(SESSIONS_FOLDER, session_id)
        plot_path = os.path.join(session_path, 'plots')
        upload_path = os.path.join(session_path, 'uploads')
        os.makedirs(plot_path, exist_ok=True)
        os.makedirs(upload_path, exist_ok=True)

        self.sessions[session_id] = {
            "id": session_id,
            "session_path": session_path,
            "plot_path": plot_path,
            "upload_path": upload_path,
            "state": { "dataframes": {}, "plots": [] },
            "llm_history": []
        }
        return self.sessions[session_id]

    def get_session(self, session_id):
        return self.sessions.get(session_id)

session_manager = SessionManager()


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

@app.route('/start_session', methods=['POST'])
def start_session():
    api_key = request.form.get('api_key')
    base_url = request.form.get('api_base_url')
    model_name = request.form.get('model_name')
    if not all([api_key, base_url, model_name]):
        return jsonify({"error": "模型设置不完整"}), 400

    files = request.files.getlist('file')
    if not files or not any(f.filename for f in files):
        return jsonify({"error": "必须提供至少一个文件"}), 400

    session = session_manager.create_session()
    
    saved_files_paths = []
    for file in files:
        if file and file.filename:
            filepath = os.path.join(session['upload_path'], file.filename)
            file.save(filepath)
            saved_files_paths.append(filepath)

    agent_core = TalkToDataCore(
        api_key=api_key, base_url=base_url, model_name=model_name,
        plot_save_dir=session['plot_path'],
        session_state=session['state']
    )

    load_messages = []
    files_to_process = [p for p in saved_files_paths if not p.lower().endswith(('.dbf', '.shx', '.prj', '.cpg', '.sbn', '.sbx'))]
    for filepath in files_to_process:
        message = agent_core.load_data_from_filepath(filepath)
        load_messages.append(message)
    
    initial_observation = "\n\n".join(load_messages)
    frontend_system_message = {'type': 'system', 'content': initial_observation}
    session['llm_history'].append({"role": "user", "content": f"数据加载完成。摘要如下：\n{initial_observation}"})

    return jsonify({
        "success": True,
        "session_id": session['id'],
        "initial_message": frontend_system_message
    })

# --- 2. 添加新的删除路由 ---
@app.route('/delete_session', methods=['POST'])
def delete_session():
    data = request.json
    session_id = data.get('session_id')
    if not session_id:
        return jsonify({"success": False, "message": "未提供 session_id"}), 400

    session = session_manager.get_session(session_id)
    if not session:
        # 即使后端内存中没有，也尝试删除可能存在的文件夹
        session_path_to_delete = os.path.join(SESSIONS_FOLDER, session_id)
        if os.path.isdir(session_path_to_delete):
            shutil.rmtree(session_path_to_delete)
        return jsonify({"success": True, "message": "会话未在内存中找到，但已尝试清理磁盘文件。"}), 200

    session_path = session.get('session_path')
    try:
        # 从磁盘上删除整个会话文件夹
        if os.path.isdir(session_path):
            shutil.rmtree(session_path)
        
        # 从后端内存中删除会话
        del session_manager.sessions[session_id]
        
        return jsonify({"success": True, "message": f"会话 {session_id} 已成功删除。"}), 200

    except Exception as e:
        return jsonify({"success": False, "message": f"删除会话时发生错误: {e}"}), 500
# -----------------------------

@app.route('/continue_analysis', methods=['POST'])
def continue_analysis():
    data = request.json
    session_id = data.get('session_id')
    task = data.get('task')
    api_key = data.get('api_key')
    base_url = data.get('api_base_url')
    model_name = data.get('model_name')
    
    if not all([session_id, task, api_key, base_url, model_name]):
        return Response('{"error": "请求参数不完整"}', status=400, mimetype='application/json')
        
    session = session_manager.get_session(session_id)
    if not session:
        return Response('{"error": "无效的 session_id"}', status=404, mimetype='application/json')

    try:
        agent_core = TalkToDataCore(
            api_key=api_key, base_url=base_url, model_name=model_name,
            plot_save_dir=session['plot_path'],
            session_state=session['state']
        )
        evaluator = Evaluator(
            api_key=api_key, base_url=base_url, model_name=model_name
        )
    except Exception as e:
         return Response(f'{{"error": "初始化核心组件失败: {e}"}}', status=500, mimetype='application/json')
    
    def generate_stream():
        history_for_report = []
        for step in agent_core.run(task, session['llm_history']):
            history_for_report.append(step)
            
            if step.get('type') == 'observation' and '图表已生成并保存于:' in str(step.get('content', '')):
                server_path = step['content'].split(":", 1)[1].strip()
                web_path = os.path.join('sessions', session_id, 'plots', os.path.basename(server_path)).replace('\\', '/')
                step['content'] = f"图表已生成并保存于: {web_path}"
            
            yield f"data: {json.dumps(step)}\n\n"

        final_summary = "任务未正常结束。"
        for item in reversed(history_for_report):
            if item.get('type') == 'final_summary':
                final_summary = item['content']
                break
        
        web_plots = [
            os.path.join('sessions', session_id, 'plots', os.path.basename(p)).replace('\\', '/')
            for p in session['state']['plots']
        ]

        evaluation = evaluator.evaluate_completion(
            task=task, final_summary=final_summary,
            history=history_for_report, generated_plots=web_plots
        )
        
        eval_chart_save_path = os.path.join(session['plot_path'], f"eval_chart_{uuid.uuid4()}.png")
        evaluator.generate_performance_chart(history=history_for_report, save_path=eval_chart_save_path)
        if os.path.exists(eval_chart_save_path):
            eval_chart_web_path = os.path.join('sessions', session_id, 'plots', os.path.basename(eval_chart_save_path)).replace('\\', '/')
            evaluation['chart_path'] = eval_chart_web_path
        else:
            evaluation['chart_path'] = None
        
        eval_message = {'type': 'evaluation', 'content': evaluation}
        yield f"data: {json.dumps(eval_message)}\n\n"

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
        msg_type_raw = message.get("type", "unknown")
        msg_type = msg_type_raw.title().replace('_', ' ')
        content = message.get("content", "")

        if msg_type_raw == 'user_request':
            task_text = content.get('task', '')
            icon_map = {'user_request': '👤'}
            markdown_content.append(f"## {icon_map.get(msg_type_raw, '💬')} 用户请求\n\n{task_text}\n")
            continue
            
        if msg_type_raw == 'action':
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
        elif msg_type_raw in ['system', 'thought', 'final_summary', 'observation']:
            icon_map = {'system': '⚙️', 'thought': '🧠', 'observation': '📊', 'final_summary': '📝'}
            markdown_content.append(f"## {icon_map.get(msg_type_raw, '💬')} {msg_type}\n\n")
            
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