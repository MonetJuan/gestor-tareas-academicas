import os,tempfile
os.environ['DATABASE_URL']='sqlite:///'+tempfile.mktemp(suffix='.db')
os.environ['JWT_SECRET']='test-only-secret-not-for-production-123456'
from main import app
from fastapi.testclient import TestClient
import jwt
from datetime import datetime,timezone,timedelta
c=TestClient(app)
def test_flow():
    def check(method,path,status,body=None,headers=None):
        r=c.request(method,path,json=body,headers=headers); print(method,path,body,'=>',r.status_code, r.text if path!='/auth/login' or status!=200 else '[token omitido]'); assert r.status_code==status; return r
    a={'username':'student','password':'Example123!'}
    check('POST','/auth/register',201,a); check('POST','/auth/register',409,a)
    check('POST','/auth/login',401,{**a,'password':'Wrong123!'})
    token=check('POST','/auth/login',200,a).json()['access_token']; h={'Authorization':'Bearer '+token}
    check('GET','/auth/validate',200,headers=h); check('GET','/auth/validate',401)
    expired=jwt.encode({'sub':'1','exp':datetime.now(timezone.utc)-timedelta(seconds=1)},os.environ['JWT_SECRET'],algorithm='HS256')
    check('GET','/auth/validate',401,headers={'Authorization':'Bearer '+expired})
    check('GET','/auth/validate',401,headers={'Authorization':'Bearer invalid'})
    for path,body in [('/projects',{'name':'Software'}),('/tasks',{'title':'Estudiar API','project_id':1})]:
        check('POST',path,401,body); check('POST',path,422,{},h)
        id=check('POST',path,201,body,h).json()['id']; item=f'{path}/{id}'
        check('GET',path,200,headers=h); check('GET',path,401)
        check('GET',item,200,headers=h); check('GET',path+'/999',404,headers=h)
        check('PUT',item,200,body,h); check('PUT',item,422,{},h); check('PUT',path+'/999',404,body,h)
        if path=='/tasks': check('POST',path,404,{**body,'project_id':999},h); check('DELETE',item,204,headers=h); check('DELETE',item,404,headers=h)
    b={'username':'other','password':'Example123!'}; check('POST','/auth/register',201,b); h2={'Authorization':'Bearer '+check('POST','/auth/login',200,b).json()['access_token']}; check('GET','/projects/1',403,headers=h2)
    check('DELETE','/projects/1',204,headers=h); check('DELETE','/projects/1',404,headers=h)
