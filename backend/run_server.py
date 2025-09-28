import uvicorn, os, sys
sys.path.append(os.path.dirname(__file__))  # para poder importar seba
if __name__ == "__main__":
    uvicorn.run("seba:app", host="127.0.0.1", port=8000, log_level="info")
