from fastapi import FastAPI
# from .endpoints import router as api_router # Será descomentado quando endpoints.py tiver conteúdo
# from src.core.company_state import CompanyState # Para injetar o estado, se necessário

app = FastAPI(
    title="Empresa Digital Autônoma API",
    description="API para interagir e monitorar a Empresa Digital Autônoma.",
    version="0.1.0"
)

# Placeholder para o estado da empresa. Em uma aplicação real, isso seria gerenciado de forma mais robusta.
# company_state_instance = CompanyState()
# app.state.company_state = company_state_instance

@app.get("/", tags=["Root"])
async def read_root():
    return {"message": "Bem-vindo à API da Empresa Digital Autônoma!"}

# app.include_router(api_router, prefix="/api/v1") # Será descomentado

# Para rodar (exemplo): uvicorn src.api.main:app --reload
