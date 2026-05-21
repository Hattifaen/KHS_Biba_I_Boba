from fastapi import FastAPI, HTTPException
import uuid
from models import (
    Seller, TradingPoint, MarketAdmin,
    FGIS_Mercury_Sync, FGIS_Saturn_Sync, Application
)

app = FastAPI(title="СХРЫНКА", version="1.0.0")

# Хранилища в памяти
sellers_db: dict[str, Seller] = {}
trading_points_db: dict[int, TradingPoint] = {}
applications_db: dict[str, Application] = {}

# Инициализация администратора и сервисов синхронизации
admin = MarketAdmin(admin_id=uuid.uuid4(), department="Отдел контроля")
mercury_sync = FGIS_Mercury_Sync()
saturn_sync = FGIS_Saturn_Sync()

# ------------------ Продавцы ------------------
@app.post("/sellers/")
def create_seller(full_name: str, irn: str, contact_phone: str):
    seller_id = str(uuid.uuid4())
    seller = Seller(id=seller_id, full_name=full_name, irn=irn, contact_phone=contact_phone)
    sellers_db[seller_id] = seller
    return {"seller_id": seller_id, "full_name": full_name}

@app.get("/sellers/{seller_id}")
def get_seller(seller_id: str):
    seller = sellers_db.get(seller_id)
    if not seller:
        raise HTTPException(status_code=404, detail="Продавец не найден")
    return {
        "id": seller.id,
        "full_name": seller.full_name,
        "irn": seller.irn,
        "contact_phone": seller.contact_phone,
        "applications": [str(app.application_id) for app in seller.applications]
    }

# ------------------ Торговые точки ------------------
@app.post("/trading-points/")
def create_trading_point(zone_name: str, square_meters: float):
    point_id = max(trading_points_db.keys(), default=0) + 1
    point = TradingPoint(point_id=point_id, zone_name=zone_name, square_meters=square_meters)
    trading_points_db[point_id] = point
    return {"point_id": point_id, "zone_name": zone_name, "rent": point.calculate_rent()}

@app.get("/trading-points/{point_id}")
def get_trading_point(point_id: int):
    point = trading_points_db.get(point_id)
    if not point:
        raise HTTPException(status_code=404, detail="Точка не найдена")
    return {
        "point_id": point.point_id,
        "zone_name": point.zone_name,
        "square_meters": point.square_meters,
        "is_occupied": point.is_occupied,
        "assigned_seller_id": point.assigned_seller_id,
        "rent": point.calculate_rent()
    }

# ------------------ Заявки ------------------
@app.post("/applications/")
def create_application(seller_id: str):
    seller = sellers_db.get(seller_id)
    if not seller:
        raise HTTPException(status_code=404, detail="Продавец не найден")
    app_obj = seller.submit_application()
    applications_db[str(app_obj.application_id)] = app_obj
    return {"application_id": str(app_obj.application_id), "status": app_obj.status}

@app.post("/applications/{application_id}/upload-docs")
def upload_docs(application_id: str, seller_id: str, doc_url: str):
    app_obj = applications_db.get(application_id)
    seller = sellers_db.get(seller_id)
    if not app_obj or not seller:
        raise HTTPException(status_code=404, detail="Заявка или продавец не найдены")
    seller.upload_document(app_obj, doc_url)
    return {"message": "Документы загружены"}

@app.post("/applications/{application_id}/sync-mercury")
def sync_mercury(application_id: str):
    app_obj = applications_db.get(application_id)
    if not app_obj:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    success = mercury_sync.send_vet_passport(app_obj)
    if success:
        mercury_sync.check_certification(app_obj)
    return {
        "success": success,
        "status_response": mercury_sync.status_response,
        "last_update": str(mercury_sync.last_update)
    }

@app.post("/applications/{application_id}/sync-saturn")
def sync_saturn(application_id: str):
    app_obj = applications_db.get(application_id)
    if not app_obj:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    success = saturn_sync.send_pesticide_report(app_obj)
    return {
        "success": success,
        "last_update": str(saturn_sync.last_update)
    }

@app.post("/applications/{application_id}/review")
def review_application(application_id: str):
    app_obj = applications_db.get(application_id)
    if not app_obj:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    approved = admin.review_application(app_obj)
    return {"application_id": application_id, "approved": approved, "new_status": app_obj.status}

@app.post("/assign-trading-point")
def assign_trading_point(seller_id: str, point_id: int):
    seller = sellers_db.get(seller_id)
    point = trading_points_db.get(point_id)
    if not seller or not point:
        raise HTTPException(status_code=404, detail="Продавец или точка не найдены")
    try:
        admin.assign_trading_point(seller, point)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"message": f"Точка {point_id} назначена продавцу {seller.full_name}"}

# Эндпоинт для проверки работоспособности
@app.get("/health")
def health():
    return {"status": "ok"}
