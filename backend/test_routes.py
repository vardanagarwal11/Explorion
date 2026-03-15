import sys
import time

print("START ROUTES TRACE", flush=True)

print("Import stdlib in routes...", flush=True)
import os
import uuid
from datetime import datetime, timedelta

print("Import fastapi in routes...", flush=True)
import fastapi
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import FileResponse, RedirectResponse

print("Import sqlalchemy in routes...", flush=True)
import sqlalchemy
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

print("Import schemas...", flush=True)
import api.schemas

print("Import db.connection...", flush=True)
import db.connection

print("Import db.queries...", flush=True)
import db.queries

print("Import rendering...", flush=True)
import rendering

print("Import jobs...", flush=True)
import jobs

print("ALL ROUTES DEPENDENCIES OK", flush=True)
