from fastapi import FastAPI, UploadFile, File

app = FastAPI()

# 🟢 Root check
@app.get("/")
def home():
    return {"message": "AI service running 🤖"}


# 🟢 Recognition endpoint (dummy for now)
@app.post("/recognize")
async def recognize(image: UploadFile = File(...)):

    # For now we are NOT doing real AI
    # Just returning dummy response

    return {
        "students": [
            {"student_id": "S101", "confidence": 0.85},
            {"student_id": "S102", "confidence": 0.78}
        ]
    }