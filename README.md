# API de tareas académicas

Servicio individual para organizar proyectos y tareas privadas. FastAPI valida entradas y genera OpenAPI; SQLite conserva relaciones mediante SQLAlchemy.

## Instalación (Python 3.11+, PowerShell)
```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
$env:JWT_SECRET = (.venv\Scripts\python -c "import secrets; print(secrets.token_hex(32))")
.venv\Scripts\python -m uvicorn main:app --reload
```
Abrir http://127.0.0.1:8000/docs. El esquema se sincroniza al iniciar con create_all; DATABASE_URL permite cambiar la ruta SQLite. No se incluyen migraciones incrementales.

## Uso
POST /auth/register y POST /auth/login reciben username y password. Copiar access_token y usar Authorize en Swagger. GET /auth/validate verifica identidad. Token HS256 de 30 minutos. Todas las rutas de recursos requieren Bearer y comprueban propiedad.

| Método | Ruta | Cuerpo | Éxito |
|---|---|---|---|
| GET | /projects, /tasks | ninguno | 200 |
| GET | /projects/{id}, /tasks/{id} | ninguno | 200 |
| POST | /projects | {"name":"Software"} | 201 |
| POST | /tasks | {"title":"Estudiar", "project_id":1,"done":false} | 201 |
| PUT | /projects/{id}, /tasks/{id} | igual a POST del recurso | 200 |
| DELETE | /projects/{id}, /tasks/{id} | ninguno | 204 |

Errores: 401 token/credenciales, 403 propiedad, 404 inexistente, 409 usuario duplicado, 422 validación. La eliminación de proyecto elimina sus tareas.

## Pruebas
`.venv\Scripts\python -m pytest -q -s` ejecuta un flujo de integración con SQLite temporal y clave exclusiva de prueba. Para evidencias manuales, repetir solicitudes en Swagger o Postman y capturar método, URL, cuerpo y respuesta, ocultando tokens.

No publicar secretos ni bases locales.
