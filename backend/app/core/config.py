import os
from pathlib import Path

class Settings:
    PROJECT_NAME: str = "GateScan"
    VERSION: str = "1.0.0"
    
    # پیدا کردن ریشه اصلی پروژه به صورت هوشمند
    # مسیر فعلی این فایل: OpenFIaaS_Project/backend/app/core/config.py
    # چهار مرحله به عقب برمی‌گردیم تا به پوشه OpenFIaaS_Project برسیم
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent.parent
    
    WORKSPACES_DIR: Path = BASE_DIR / "workspaces"
    ENGINE_DIR: Path = BASE_DIR / "glfi_engine"
    
    # ایجاد خودکار پوشه فضاهای کاری اگر وجود نداشت
    def __init__(self):
        self.WORKSPACES_DIR.mkdir(parents=True, exist_ok=True)

settings = Settings()