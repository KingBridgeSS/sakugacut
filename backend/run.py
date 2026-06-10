from __future__ import annotations

import uvicorn


if __name__ == "__main__":
    uvicorn.run("backend.asgi:asgi_app", host="0.0.0.0", port=5001, reload=True)
