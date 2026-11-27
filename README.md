# API de tareas académicas

API para organizar los trabajos de un estudiante por proyectos. Cada proyecto puede contener varias tareas, y cada usuario solo tiene acceso a sus propios datos. El servicio utiliza FastAPI, SQLite y SQLAlchemy.

## Instalación (Python 3.11+, PowerShell)
Descargar el proyecto desde Code > Download ZIP o clonarlo con Git. Abrir PowerShell dentro de la carpeta del proyecto.

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
$env:JWT_SECRET = (.venv\Scripts\python -c "import secrets; print(secrets.token_hex(32))")
.venv\Scripts\python -m uvicorn main:app --reload
```
Abrir http://127.0.0.1:8000/docs. El esquema se sincroniza al iniciar con create_all; DATABASE_URL permite cambiar la ruta SQLite. No se incluyen migraciones incrementales.

## Uso
1. En Swagger, ejecutar `POST /auth/register` con un usuario de prueba, por ejemplo `{"username":"estudiante","password":"Ejemplo123!"}`.
2. Usar los mismos datos en `POST /auth/login`. Copiar el valor de `access_token` y pegarlo en Authorize (sin escribir Bearer dos veces).
3. Crear un proyecto con `POST /projects`, copiar el ID de la respuesta y usarlo como `project_id` al crear una tarea.
4. Consultar, modificar o eliminar los registros. `GET /auth/validate` comprueba el token.

El token está firmado con HS256 y vence después de 30 minutos. Todas las rutas de proyectos y tareas requieren autenticación y verifican la propiedad del recurso.

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
`.venv\Scripts\python -m pytest -q -s` ejecuta un flujo de integración con SQLite temporal y clave exclusiva de prueba. El archivo `evidencia_pruebas.txt` contiene un registro de ejecución. Para repetir las pruebas manualmente, se puede utilizar Swagger, Postman o curl. No compartir tokens ni credenciales reales.

## Alcance

El código está concentrado en `main.py` por el tamaño del ejercicio. Como mejora futura se propone separar modelos, seguridad y rutas, así como incorporar migraciones versionadas.

No publicar secretos ni bases locales.
