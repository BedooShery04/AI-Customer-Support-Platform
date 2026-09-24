from fastapi import FastAPI

from app.routers import auth
from app.routers import tickets


app = FastAPI(
    title="AI Customer Support Platform"
)


app.include_router(auth.router)
app.include_router(tickets.router)

