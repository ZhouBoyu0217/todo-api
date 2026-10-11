from fastapi import FastAPI          # 老熟人：框架
from pydantic import BaseModel       # 新人：数据模型工具，用来"声明数据长什么样"
import sqlite3

app = FastAPI()                      # 后厨开业
conn = sqlite3.connect("todos.db", check_same_thread=False)    # 连接数据库文件，没有就自动创建
conn.execute("""CREATE TABLE IF NOT EXISTS todos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL
)""")                                  # 建表：一张带自增主键的任务表
conn.commit()

class Todo(BaseModel):               # 声明一张"表格"：这个接口接收的数据
    content: str                     # 只有一个字段 content，必须是字符串

@app.get("/")
def hello():                         # 老接口，不动
    return {"message": "Hello, 秋招！"}

@app.post("/todos")
def add_todo(todo: Todo):
    conn.execute("INSERT INTO todos (content) VALUES (?)", (todo.content,))
    conn.commit()
    new_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    return {"message": "已添加", "id": new_id, "content": todo.content}

@app.get("/todos")
def list_todos():
    rows = conn.execute("SELECT id, content FROM todos").fetchall()
    return [{"id": r[0], "content": r[1]} for r in rows]
@app.put("/todos/{id}")
def update_todo(id: int, todo: Todo):
    cur = conn.execute("UPDATE todos SET content = ? WHERE id = ?", (todo.content, id))
    conn.commit()
    if cur.rowcount > 0:
        return {"message": "已修改", "content": todo.content}
    return {"message": "不存在相应编号"}
@app.delete("/todos/{id}")
def delete_todo(id: int):
    cur = conn.execute("DELETE FROM todos WHERE id = ?", (id,))
    conn.commit()
    if cur.rowcount > 0:
        return {"message": f"已删除编号为{id}的任务！"}
    return {"message": "不存在相应编号"}

