from fastapi import FastAPI
from app.routers import auth
from app.routers import tickets
from app.routers import ai

app = FastAPI(title="AI Customer Support Platform")

app.include_router(auth.router)
app.include_router(tickets.router)
app.include_router(ai.router)


