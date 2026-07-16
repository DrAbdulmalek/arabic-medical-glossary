"""
واجهة سطر أوامر لتشغيل API.
"""
import uvicorn

if __name__ == "__main__":
    import os
    port = int(os.getenv("API_PORT", "8000"))
    uvicorn.run("api.main:app", host="0.0.0.0", port=port, reload=True)