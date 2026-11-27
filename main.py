import os, hashlib, secrets, hmac
from datetime import datetime, timedelta, timezone
import jwt
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import create_engine, ForeignKey, String, event, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session

engine=create_engine(os.getenv('DATABASE_URL','sqlite:///academico.db'),connect_args={'check_same_thread':False})
@event.listens_for(engine,'connect')
def foreign_keys(dbapi, _):
    dbapi.execute('PRAGMA foreign_keys=ON')
class Base(DeclarativeBase): pass
class User(Base):
    __tablename__='users'
    id: Mapped[int]=mapped_column(primary_key=True)
    username: Mapped[str]=mapped_column(String(40),unique=True)
    password_hash: Mapped[str]=mapped_column(String(200))
class Project(Base):
    __tablename__='projects'
    id: Mapped[int]=mapped_column(primary_key=True)
    name: Mapped[str]=mapped_column(String(100))
    owner_id: Mapped[int]=mapped_column(ForeignKey('users.id'))
class Task(Base):
    __tablename__='tasks'
    id: Mapped[int]=mapped_column(primary_key=True)
    title: Mapped[str]=mapped_column(String(120))
    done: Mapped[bool]=mapped_column(default=False)
    project_id: Mapped[int]=mapped_column(ForeignKey('projects.id',ondelete='CASCADE'))
Base.metadata.create_all(engine)
class Credentials(BaseModel):
    username: str=Field(min_length=3,max_length=40,pattern=r'^[a-zA-Z0-9_]+$')
    password: str=Field(min_length=8,max_length=128)
class ProjectIn(BaseModel):
    model_config=ConfigDict(str_strip_whitespace=True,extra='forbid')
    name: str=Field(min_length=1,max_length=100)
class TaskIn(BaseModel):
    model_config=ConfigDict(str_strip_whitespace=True,extra='forbid')
    title: str=Field(min_length=1,max_length=120)
    done: bool=False
    project_id: int=Field(gt=0)
app=FastAPI(title='API de tareas académicas')
@app.exception_handler(RequestValidationError)
async def validation(request:Request, exc:RequestValidationError):
    return JSONResponse(status_code=422,content={'detail':[{'field':'.'.join(map(str,e['loc'])),'message':e['msg']} for e in exc.errors()]})
def db():
    with Session(engine) as s: yield s
def hash_password(password,salt):
    return hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),600000).hex()
def secret():
    key=os.environ.get('JWT_SECRET','')
    if len(key)<32: raise HTTPException(503,'Configure JWT_SECRET')
    return key
bearer=HTTPBearer(auto_error=False)
def current(auth:HTTPAuthorizationCredentials=Depends(bearer),s:Session=Depends(db)):
    try:
        if not auth: raise ValueError()
        data=jwt.decode(auth.credentials,secret(),algorithms=['HS256'],options={'require':['exp','sub']})
        user=s.get(User,int(data['sub']))
        if not user: raise ValueError()
        return user
    except (jwt.InvalidTokenError,ValueError,TypeError): raise HTTPException(401,'Token ausente, inválido o vencido',headers={'WWW-Authenticate':'Bearer'})
@app.post('/auth/register',status_code=201)
def register(body:Credentials,s:Session=Depends(db)):
    if s.scalar(select(User).where(User.username==body.username)): raise HTTPException(409,'Usuario existente')
    salt=secrets.token_hex(16); u=User(username=body.username,password_hash=salt+':'+hash_password(body.password,salt)); s.add(u); s.commit(); return {'id':u.id,'username':u.username}
@app.post('/auth/login')
def login(body:Credentials,s:Session=Depends(db)):
    u=s.scalar(select(User).where(User.username==body.username))
    if not u: raise HTTPException(401,'Credenciales incorrectas')
    salt,digest=u.password_hash.split(':')
    if not hmac.compare_digest(digest,hash_password(body.password,salt)): raise HTTPException(401,'Credenciales incorrectas')
    return {'access_token':jwt.encode({'sub':str(u.id),'exp':datetime.now(timezone.utc)+timedelta(minutes=30)},secret(),algorithm='HS256'),'token_type':'bearer'}
@app.get('/auth/validate')
def validate(u:User=Depends(current)): return {'id':u.id,'username':u.username}
def owned(s,model,id,u):
    obj=s.get(model,id)
    if not obj: raise HTTPException(404,'Recurso inexistente')
    owner=obj.owner_id if model is Project else s.get(Project,obj.project_id).owner_id
    if owner!=u.id: raise HTTPException(403,'Acceso no autorizado')
    return obj
def serialize(obj): return {c.name:getattr(obj,c.name) for c in obj.__table__.columns}
def routes(model,schema,path):
    def collection(s:Session=Depends(db),u:User=Depends(current)):
        q=select(model).where(Project.owner_id==u.id) if model is Project else select(Task).join(Project).where(Project.owner_id==u.id)
        return [serialize(x) for x in s.scalars(q)]
    def item(id:int,s:Session=Depends(db),u:User=Depends(current)): return serialize(owned(s,model,id,u))
    def create(body:schema,s:Session=Depends(db),u:User=Depends(current)):
        data=body.model_dump()
        if model is Task: owned(s,Project,body.project_id,u)
        else: data['owner_id']=u.id
        obj=model(**data); s.add(obj); s.commit(); return serialize(obj)
    def update(id:int,body:schema,s:Session=Depends(db),u:User=Depends(current)):
        obj=owned(s,model,id,u)
        if model is Task: owned(s,Project,body.project_id,u)
        for k,v in body.model_dump().items(): setattr(obj,k,v)
        s.commit(); return serialize(obj)
    def delete(id:int,s:Session=Depends(db),u:User=Depends(current)):
        s.delete(owned(s,model,id,u)); s.commit()
    for fn,method,suffix,status in [(collection,'GET','',200),(item,'GET','/{id}',200),(create,'POST','',201),(update,'PUT','/{id}',200),(delete,'DELETE','/{id}',204)]:
        app.add_api_route(path+suffix,fn,methods=[method],status_code=status,name=method+' '+path+suffix)
routes(Project,ProjectIn,'/projects')
routes(Task,TaskIn,'/tasks')
