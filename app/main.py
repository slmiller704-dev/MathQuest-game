from __future__ import annotations
import random, time, uuid
from dataclasses import dataclass, field
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

app=FastAPI(title='MathQuest Live Learning Battles',version='2.0')
app.mount('/static',StaticFiles(directory='static'),name='static')

@dataclass
class Session:
    grade:int; archetype:str; variant:str; level:int=1; xp:int=0; coins:int=0
    hp:int=100; enemy_hp:int=100; streak:int=0; mastery:dict=field(default_factory=dict)
    answer:float=0; prompt:str=''; skill:str=''; hint:str=''; started:float=field(default_factory=time.time)
SESSIONS:dict[str,Session]={}

STATS={'Knight':(125,12,'Fortify'),'Wizard':(95,14,'Insight'),'Engineer':(105,11,'Optimize'),'Ranger':(105,12,'Precision'),'Ninja':(95,12,'Quick Think'),'Paladin':(130,10,'Encourage'),'Fairy':(90,9,'Spark of Insight'),'Jester':(100,11,'Wildcard'),'Warlock':(105,15,'Arcane Equation')}

class Start(BaseModel): grade:int=Field(ge=4,le=12); archetype:str; variant:str=Field(pattern='^(boy|girl)$')
class Answer(BaseModel): session_id:str; answer:float; seconds:float=Field(default=10,ge=0,le=300)
class Ability(BaseModel): session_id:str

def make_problem(s:Session,easier=False):
    weakest=min(s.mastery,key=s.mastery.get) if s.mastery else None
    if s.grade<=5:
        skills=['multiplication','division','fractions']; skill=weakest if weakest in skills else random.choice(skills)
        if skill=='multiplication':
            a,b=random.randint(2,12),random.randint(2,12); prompt=f'{a} × {b} = ?'; ans=a*b; hint=f'Break {a} × {b} into smaller facts.'
        elif skill=='division':
            b=random.randint(2,12); ans=random.randint(2,12); a=b*ans; prompt=f'{a} ÷ {b} = ?'; hint='Ask which number multiplied by the divisor gives the dividend.'
        else:
            d=random.choice([2,4,5,10]); n=random.randint(1,d-1); prompt=f'Write {n}/{d} as a decimal.'; ans=n/d; hint=f'Divide {n} by {d}.'
    elif s.grade<=8:
        skill=weakest if weakest in {'equations','percent','integers'} else random.choice(['equations','percent','integers'])
        if skill=='equations':
            x=random.randint(2,14); a=random.randint(2,8); b=random.randint(1,18); prompt=f'Solve: {a}x + {b} = {a*x+b}'; ans=x; hint=f'Subtract {b}, then divide by {a}.'
        elif skill=='percent':
            pct=random.choice([10,20,25,50,75]); base=random.choice([20,40,60,80,100,120]); prompt=f'What is {pct}% of {base}?'; ans=pct*base/100; hint='Convert the percent to a decimal, then multiply.'
        else:
            a=random.randint(-15,15); b=random.randint(-15,15); prompt=f'{a} + ({b}) = ?'; ans=a+b; hint='Use a number line and watch the signs.'
    else:
        skill=weakest if weakest in {'algebra','functions','geometry'} else random.choice(['algebra','functions','geometry'])
        if skill=='algebra':
            x=random.randint(-6,8); prompt=f'Evaluate x² + 3x + 2 when x = {x}'; ans=x*x+3*x+2; hint='Substitute x carefully, including parentheses for negatives.'
        elif skill=='functions':
            x=random.randint(-5,8); prompt=f'If f(x)=2x−5, find f({x}).'; ans=2*x-5; hint='Replace every x with the given input.'
        else:
            w=random.randint(3,15); h=random.randint(3,15); prompt=f'A rectangle is {w} by {h}. What is its area?'; ans=w*h; hint='Area equals length times width.'
    if easier and s.grade>5:
        a,b=random.randint(2,9),random.randint(2,9); prompt=f'{a} × {b} = ?'; ans=a*b; skill='review'; hint='Use a known multiplication fact.'
    s.prompt,s.answer,s.skill,s.hint=prompt,float(ans),skill,hint

def view(sid,s,event='ready',message=''):
    return {'session_id':sid,'event':event,'message':message,'character':{'archetype':s.archetype,'variant':s.variant,'level':s.level,'xp':s.xp,'coins':s.coins,'ability':STATS[s.archetype][2]},'battle':{'hp':s.hp,'enemy_hp':s.enemy_hp,'prompt':s.prompt,'skill':s.skill,'streak':s.streak},'mastery':s.mastery}

@app.get('/')
def home(): return FileResponse('static/index.html')
@app.get('/health')
def health(): return {'status':'ok'}
@app.post('/api/start')
def start(x:Start):
    if x.archetype not in STATS: raise HTTPException(422,'Unknown character')
    sid=uuid.uuid4().hex; s=Session(grade=x.grade,archetype=x.archetype,variant=x.variant,hp=STATS[x.archetype][0]); make_problem(s); SESSIONS[sid]=s
    return view(sid,s,'battle_start',f'{x.variant.title()} {x.archetype} entered the arena!')
@app.post('/api/answer')
def answer(x:Answer):
    s=SESSIONS.get(x.session_id)
    if not s: raise HTTPException(404,'Session expired. Start a new battle.')
    correct=abs(x.answer-s.answer)<0.001; base=15+STATS[s.archetype][1]; event='miss'; msg='The guardian counterattacks. Study the hint and recover.'
    prior=s.mastery.get(s.skill,50)
    if correct:
        speed_bonus=max(0,10-int(x.seconds)); damage=base+speed_bonus+s.streak*2; s.enemy_hp=max(0,s.enemy_hp-damage); s.streak+=1; gain=20+min(10,s.streak*2); s.xp+=gain; s.coins+=5; s.mastery[s.skill]=min(100,prior+5); event='hit'; msg=f'Correct! {damage} damage, +{gain} XP.'
    else:
        s.hp=max(0,s.hp-15); s.streak=0; s.mastery[s.skill]=max(0,prior-3)
    leveled=False
    while s.xp>=s.level*100:
        s.xp-=s.level*100; s.level+=1; s.coins+=50; leveled=True
    if s.enemy_hp<=0:
        s.coins+=25; event='victory'; msg='Victory! Reward chest opened: +25 coins.'
    elif s.hp<=0:
        event='defeat'; msg='The guardian won this round. Your mastery data will guide the next lesson.'
    else: make_problem(s)
    if leveled: msg+=f' Level up! You reached level {s.level}.'
    return view(x.session_id,s,event,msg)
@app.post('/api/ability')
def ability(x:Ability):
    s=SESSIONS.get(x.session_id)
    if not s: raise HTTPException(404,'Session expired')
    a=STATS[s.archetype][2]; msg=''
    if a=='Fortify': s.hp=min(STATS[s.archetype][0],s.hp+15); msg='Fortify restored 15 HP.'
    elif a=='Insight': msg='Insight: '+s.hint
    elif a=='Optimize': msg=f'Optimize: the answer is {"even" if int(s.answer)%2==0 else "odd"}.'
    elif a=='Precision': s.enemy_hp=max(0,s.enemy_hp-20); msg='Precision dealt 20 strategic damage.'
    elif a=='Quick Think': s.xp+=10; msg='Quick Think awarded 10 XP.'
    elif a=='Encourage': s.hp=min(STATS[s.archetype][0],s.hp+25); msg='Encourage restored 25 HP.'
    elif a=='Spark of Insight': s.hp=min(STATS[s.archetype][0],s.hp+10); msg='Spark of Insight: '+s.hint+' You also healed 10 HP.'
    elif a=='Wildcard':
        reward=random.choice(['heal','damage','coins'])
        if reward=='heal': s.hp=min(STATS[s.archetype][0],s.hp+20); msg='Wildcard healed 20 HP.'
        elif reward=='damage': s.enemy_hp=max(0,s.enemy_hp-30); msg='Wildcard dealt 30 damage.'
        else: s.coins+=15; msg='Wildcard awarded 15 coins.'
    else: make_problem(s,True); msg='Arcane Equation transformed the problem into an easier review challenge.'
    return view(x.session_id,s,'ability',msg)
