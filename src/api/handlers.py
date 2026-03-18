from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()


@app.get("/auth/")
def who_i_am():
    return {"message": "I am auth service! And I was changed!"}

@app.get("/health")
async def health_check():
    return JSONResponse({"status": "healthy"})
