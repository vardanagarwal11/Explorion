import sys
import time
print("START", flush=True)
try:
    print("Loading dotenv...", flush=True)
    from dotenv import load_dotenv
    load_dotenv()
    print("Dotenv loaded", flush=True)

    print("Importing fastapi...", flush=True)
    import fastapi
    print("Fastapi loaded", flush=True)

    print("Importing routes...", flush=True)
    from api.routes import router
    print("Routes loaded", flush=True)

    print("Importing db...", flush=True)
    from db import init_db
    print("DB loaded", flush=True)

    print("ALL OK", flush=True)
except Exception as e:
    print(f"ERROR: {e}", flush=True)
