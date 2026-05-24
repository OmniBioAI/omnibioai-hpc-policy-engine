import json
import os
import pathlib

from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse, Response
from swagger_ui_bundle import swagger_ui_path

_swagger_js = pathlib.Path(swagger_ui_path, "swagger-ui-bundle.js").read_text()
_swagger_css = pathlib.Path(swagger_ui_path, "swagger-ui.css").read_text()

from app.db.session import Base, engine

from app.api.routes_policy import router as policy_router
from app.api.routes_quota import router as quota_router

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="OmniBioAI HPC Policy Engine",
    root_path="/_svc/hpc",
    docs_url=None,
    redoc_url=None,
)
app.openapi_version = "3.0.3"

_MIME = {
    ".js": "application/javascript",
    ".css": "text/css",
    ".html": "text/html",
    ".png": "image/png",
    ".map": "application/json",
}


@app.get("/swagger-static/{path:path}", include_in_schema=False)
async def swagger_static(path: str) -> Response:
    full = os.path.join(swagger_ui_path, path)
    if not os.path.isfile(full):
        return Response(status_code=404)
    return FileResponse(full, media_type=_MIME.get(os.path.splitext(full)[1], "application/octet-stream"))


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui() -> HTMLResponse:
    spec_json = json.dumps(app.openapi()).replace("</", "<\\/")
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>OmniBioAI HPC Policy Engine</title>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>{_swagger_css}</style>
</head>
<body>
<div id="swagger-ui"></div>
<script>{_swagger_js}</script>
<script>
SwaggerUIBundle({{
    spec: {spec_json},
    dom_id: '#swagger-ui',
    presets: [SwaggerUIBundle.presets.apis, SwaggerUIBundle.SwaggerUIStandalonePreset],
    layout: 'BaseLayout',
    deepLinking: true,
    validatorUrl: null,
}})
</script>
</body>
</html>"""
    return HTMLResponse(html)


app.include_router(policy_router)
app.include_router(quota_router)


@app.get("/")
async def root():
    return {
        "service": "omnibioai-hpc-policy-engine",
        "status": "running",
    }