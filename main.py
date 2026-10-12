from fastapi import FastAPI          # 老熟人：框架
from fastapi.staticfiles import StaticFiles   # 托管前端页面
from pydantic import BaseModel       # 新人：数据模型工具，用来"声明数据长什么样"
import sqlite3
import os
import json
import re
from openai import OpenAI
from dotenv import load_dotenv
app = FastAPI()# 后厨开业
load_dotenv()
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)
conn = sqlite3.connect("todos.db", check_same_thread=False)    # 连接数据库文件，没有就自动创建
conn.execute("""CREATE TABLE IF NOT EXISTS todos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    done INTEGER NOT NULL DEFAULT 0,
    due_time TEXT,
    category TEXT DEFAULT '未分类'
)""")                                  # 建表：done=1已完成；due_time=截止时间；category=分类
conn.commit()

# 老数据库升级：检测到缺失的列就补上，老数据不受影响
cols = [row[1] for row in conn.execute("PRAGMA table_info(todos)")]
if "done" not in cols:
    conn.execute("ALTER TABLE todos ADD COLUMN done INTEGER NOT NULL DEFAULT 0")
if "due_time" not in cols:
    conn.execute("ALTER TABLE todos ADD COLUMN due_time TEXT")
if "category" not in cols:
    conn.execute("ALTER TABLE todos ADD COLUMN category TEXT DEFAULT '未分类'")
conn.commit()

class Todo(BaseModel):               # 声明一张"表格"：这个接口接收的数据
    content: str    # 只有一个字段 content，必须是字符串

class AITodo(BaseModel):
    text: str
def row_to_dict(r):                  # 把数据库一行转成接口返回的字典
    return {"id": r[0], "content": r[1], "done": bool(r[2]), "due_time": r[3], "category": r[4]}

@app.get("/api/hello")
def hello():                         # 老接口，挪到 /api/hello（根路径让给前端页面）
    return {"message": "Hello, 秋招！"}

@app.post("/todos")
def add_todo(todo: Todo):
    conn.execute("INSERT INTO todos (content, done) VALUES (?, 0)", (todo.content,))
    conn.commit()
    new_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    return {"message": "已添加", "id": new_id, "content": todo.content, "done": False}

@app.get("/todos")
def list_todos():
    rows = conn.execute("SELECT id, content, done, due_time, category FROM todos ORDER BY id").fetchall()
    return [row_to_dict(r) for r in rows]

@app.put("/todos/{id}")
def update_todo(id: int, todo: Todo):
    cur = conn.execute("UPDATE todos SET content = ? WHERE id = ?", (todo.content, id))
    conn.commit()
    if cur.rowcount > 0:
        return {"message": "已修改", "content": todo.content}
    return {"message": "不存在相应编号"}

@app.put("/todos/{id}/toggle")
def toggle_todo(id: int):
    # 勾选/取消完成：done 在 0 和 1 之间翻转
    cur = conn.execute("UPDATE todos SET done = 1 - done WHERE id = ?", (id,))
    conn.commit()
    if cur.rowcount > 0:
        done = conn.execute("SELECT done FROM todos WHERE id = ?", (id,)).fetchone()[0]
        return {"message": "已切换", "id": id, "done": bool(done)}
    return {"message": "不存在相应编号"}

@app.delete("/todos/{id}")
def delete_todo(id: int):
    cur = conn.execute("DELETE FROM todos WHERE id = ?", (id,))
    conn.commit()
    if cur.rowcount > 0:
        return {"message": f"已删除编号为{id}的任务！"}
    return {"message": "不存在相应编号"}

@app.post("/todos/ai")
def ai_add_todo(item: AITodo):
    system_prompt = (
        "你是任务解析助手。把用户的话解析成 JSON，包含三个字段：\n"
        '{"content": "纯任务内容（去掉时间等修饰）", '
        '"due_time": "任务时间，如 明天下午三点；没有则填 null", '
        '"category": "学习/生活/工作 三者之一"}。\n'
        "只输出 JSON，不要任何其他文字。"
    )
    resp = client.chat.completions.create(
        model="deepseek-v4-pro",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": item.text},
        ],
    )
    raw = resp.choices[0].message.content
    # 容错解析：大模型常把 JSON 包在 ```json 围栏里，或前后加废话，先剥壳再解析
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-zA-Z]*\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    try:
        data = json.loads(raw)
    except Exception:
        start, end = raw.find("{"), raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                data = json.loads(raw[start:end + 1])
            except Exception:
                data = {}
        else:
            data = {}
    content = data.get("content") or item.text
    due_time = data.get("due_time")
    category = data.get("category") or "未分类"
    conn.execute(
        "INSERT INTO todos (content, done, due_time, category) VALUES (?, 0, ?, ?)",
        (content, due_time, category),
    )
    conn.commit()
    new_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    return {"message": "已添加", "id": new_id, "content": content, "due_time": due_time, "category": category}

# 托管前端：把 static 目录挂到根路径，访问 http://127.0.0.1:8000/ 就是页面
# html=True 表示访问目录时自动返回里面的 index.html
# 注意：这一行要放在所有接口定义之后，否则会把 /todos 这些路由也吃掉
app.mount("/", StaticFiles(directory="static", html=True), name="static")