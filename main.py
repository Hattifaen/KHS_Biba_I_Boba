from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uuid
from models import (
    Seller,
    TradingPoint,
    MarketAdmin,
    FGIS_Mercury_Sync,
    FGIS_Saturn_Sync,
    ApplicationStatus,
    Application,
)

app = FastAPI(title="СХРЫНКА", version="2.0.0")

# Подключаем статику и шаблоны
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Хранилища в памяти
sellers_db: dict[str, Seller] = {}
trading_points_db: dict[int, TradingPoint] = {}
applications_db: dict[str, Application] = {}

# Инициализация
admin = MarketAdmin(admin_id=uuid.uuid4(), department="Отдел контроля")
mercury_sync = FGIS_Mercury_Sync()
saturn_sync = FGIS_Saturn_Sync()


# ==================== ВЕБ-СТРАНИЦЫ ====================


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    free = sum(1 for p in trading_points_db.values() if not p.is_occupied)
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "sellers_count": len(sellers_db),
            "points_count": len(trading_points_db),
            "applications_count": len(applications_db),
            "free_points": free,
        },
    )


@app.get("/sellers", response_class=HTMLResponse)
async def sellers_page(request: Request):
    return templates.TemplateResponse(
        "sellers.html", {"request": request, "sellers": sellers_db.values()}
    )


@app.get("/sellers/add", response_class=HTMLResponse)
async def add_seller_page(request: Request):
    return templates.TemplateResponse("add_seller.html", {"request": request})


@app.post("/sellers/add")
async def add_seller(
    full_name: str = Form(...), irn: str = Form(...), contact_phone: str = Form(...)
):
    seller_id = str(uuid.uuid4())
    seller = Seller(
        id=seller_id, full_name=full_name, irn=irn, contact_phone=contact_phone
    )
    sellers_db[seller_id] = seller
    return RedirectResponse(url="/sellers", status_code=303)


@app.get("/sellers/{seller_id}", response_class=HTMLResponse)
async def seller_detail(request: Request, seller_id: str):
    seller = sellers_db.get(seller_id)
    if not seller:
        raise HTTPException(status_code=404, detail="Продавец не найден")
    return templates.TemplateResponse(
        "seller_detail.html", {"request": request, "seller": seller}
    )


@app.get("/points", response_class=HTMLResponse)
async def points_page(request: Request):
    return templates.TemplateResponse(
        "points.html", {"request": request, "points": trading_points_db.values()}
    )


@app.get("/applications", response_class=HTMLResponse)
async def applications_page(request: Request, status: str = None):
    apps_list = []
    for app in applications_db.values():
        seller = sellers_db.get(str(app.seller_id))
        if seller:
            if status is None or app.status.value == status:
                apps_list.append({"application": app, "seller": seller})

    # Сортировка: новые сверху
    apps_list.sort(key=lambda x: x["application"].created_at, reverse=True)

    return templates.TemplateResponse(
        "applications.html", {"request": request, "applications": apps_list}
    )


@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    # Заявки на рассмотрении
    pending = []
    for app in applications_db.values():
        if app.status in [ApplicationStatus.NEW, ApplicationStatus.VERIFYING]:
            seller = sellers_db.get(str(app.seller_id))
            if seller:
                pending.append({"application": app, "seller": seller})

    # Свободные точки
    free_points = [p for p in trading_points_db.values() if not p.is_occupied]

    return templates.TemplateResponse(
        "admin.html",
        {
            "request": request,
            "pending_apps": pending,
            "all_sellers": sellers_db.values(),
            "free_points_list": free_points,
        },
    )


@app.post("/admin/review/{application_id}")
async def admin_review_action(application_id: str):
    app_obj = applications_db.get(application_id)
    if not app_obj:
        raise HTTPException(status_code=404)

    admin.review_application(app_obj)
    return RedirectResponse(url="/admin", status_code=303)


@app.post("/admin/assign-point")
async def admin_assign_point(seller_id: str = Form(...), point_id: int = Form(...)):
    seller = sellers_db.get(seller_id)
    point = trading_points_db.get(point_id)

    if not seller or not point:
        raise HTTPException(status_code=404)

    try:
        admin.assign_trading_point(seller, point)
    except ValueError:
        pass  # Точка уже занята

    return RedirectResponse(url="/admin", status_code=303)


# ==================== API (для программного доступа) ====================


@app.post("/api/sellers/")
def create_seller_api(full_name: str, irn: str, contact_phone: str):
    seller_id = str(uuid.uuid4())
    seller = Seller(
        id=seller_id, full_name=full_name, irn=irn, contact_phone=contact_phone
    )
    sellers_db[seller_id] = seller
    return {"seller_id": seller_id}


@app.post("/api/points/")
def create_point_api(zone_name: str, square_meters: float):
    point_id = max(trading_points_db.keys(), default=0) + 1
    point = TradingPoint(
        point_id=point_id, zone_name=zone_name, square_meters=square_meters
    )
    trading_points_db[point_id] = point
    return {"point_id": point_id}


@app.post("/applications/create/{seller_id}")
async def create_application_action(seller_id: str):
    seller = sellers_db.get(seller_id)
    if not seller:
        raise HTTPException(status_code=404)

    app_obj = seller.submit_application()
    applications_db[str(app_obj.application_id)] = app_obj

    # Автосинхронизация
    seller.upload_document(app_obj, "https://docs.example.com/auto.pdf")
    mercury_sync.send_vet_passport(app_obj)
    mercury_sync.check_certification(app_obj)
    saturn_sync.send_pesticide_report(app_obj)

    return RedirectResponse(url=f"/sellers/{seller_id}", status_code=303)


@app.get("/health")
def health():
    return {"status": "ok"}
