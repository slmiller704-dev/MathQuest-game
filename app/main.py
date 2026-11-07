import random
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
app=FastAPI(title='MathQuest Game MVP')
app.mount('/static',StaticFiles(directory='static'),name='static')
class Answer(BaseModel): grade:int; answer:int
@app.get('/')
def home(): return FileResponse('static/index.html')
@app.get('/health')
def health(): return {'status':'ok'}
@app.get('/api/question/{grade}')
def question(grade:int):
    if grade<=5: a,b=random.randint(2,12),random.randint(2,12)
    else: a,b=random.randint(4,20),random.randint(2,12)
    return {'prompt':f'{a} x {b} = ?','answer':a*b}
