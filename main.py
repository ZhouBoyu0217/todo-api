from fastapi import FastAPI          # 老熟人：框架
from fastapi.staticfiles import StaticFiles   # 托管前端页面
from pydantic import BaseModel       # 新人：数据模型工具，用来"声明数据长什么样"
import sqlite3

app = FastAPI()                      # 后厨开业
conn = sqlite3.connect("todos.db", check_same_thread=False)    # 连接数据库文件，没有就自动创建
conn.execute("""CREATE TABLE IF NOT EXISTS todos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    done INTEGER NOT NULL DEFAULT 0
)""")                                  # 建表：一张带自增主键的任务表（done=1 表示已完成）
conn.commit()

# v4 升级：老数据库里没有 done 列，检测到就补上，老数据不受影响
cols = [row[1] for row in conn.execute("PRAGMA table_info(todos)")]
if "done" not in cols:
    conn.execute("ALTER TABLE todos ADD COLUMN done INTEGER NOT NULL DEFAULT 0")
    conn.commit()

class Todo(BaseModel):               # 声明一张"表格"：这个接口接收的数据
    content: str                     # 只有一个字段 content，必须是字符串

def row_to_dict(r):                  # 把数据库一行转成接口返回的字典
    return {"id": r[0], "content": r[1], "done": bool(r[2])}

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
    rows = conn.execute("SELECT id, content, done FROM todos ORDER BY id").fetchall()
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

# 托管前端：把 static 目录挂到根路径，访问 http://127.0.0.1:8000/ 就是页面
# html=True 表示访问目录时自动返回里面的 index.html
# 注意：这一行要放在所有接口定义之后，否则会把 /todos 这些路由也吃掉
app.mount("/", StaticFiles(directory="static", html=True), name="static")
