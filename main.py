from fastapi import FastAPI          # 老熟人：框架
from pydantic import BaseModel       # 新人：数据模型工具，用来"声明数据长什么样"

app = FastAPI()                      # 后厨开业

todos = []                           # 任务清单。注意它只是内存里的一个空列表，
next_id=1                                    # 服务一重启就归零（v3 才换数据库）

class Todo(BaseModel):               # 声明一张"表格"：这个接口接收的数据
    content: str                     # 只有一个字段 content，必须是字符串

@app.get("/")
def hello():                         # 老接口，不动
    return {"message": "Hello, 秋招！"}

@app.post("/todos")                  # 新接口：谁 POST 到 /todos，就执行下面这个函数
def add_todo(todo: Todo):
    global next_id
    todos.append({"id":next_id,"content":todo.content})  # 解析成 Todo 对象，你直接拿来用
    next_id+=1
    return {"message": "已添加","id":next_id-1, "content": todo.content}  # 回执
@app.get("/todos")
def check_todos():
    return todos
@app.put("/todos/{id}")
def put_todos(todo:Todo,id:int):
    flag=False
    for i in todos:
        if i["id"]==id:
            i["content"]=todo.content
    if flag:
        return {"message":"已修改","编号":id,"content":todo.content}
    else:
        return {"message":"不存在相应编号"}
@app.delete("/todos/{id}")
def delete_todos(id:int):
    target=[]
    for i in todos:
        if i["id"]==id:
            target.append(i)
    for i in target:
        todos.remove(i)
    if target:
        return {"message":f"已删除编号为{id}的任务！"}
    else:
        return {"message":"不存在相应编号"}

