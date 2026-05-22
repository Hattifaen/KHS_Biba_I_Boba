import pytest
import uuid
from models import (
    Seller,
    Application,
    TradingPoint,
    MarketAdmin,
    FGIS_Mercury_Sync,
    FGIS_Saturn_Sync,
    ApplicationStatus,
)


# ТЕСТЫ SELLER


def test_seller_creation():
    # Проверяет создание продавца с правильными атрибутами
    seller_id = str(uuid.uuid4())
    seller = Seller(
        id=seller_id,
        full_name="Иван Петров",
        irn="1234567890",
        contact_phone="+79001234567",
    )

    assert seller.id == seller_id
    assert seller.full_name == "Иван Петров"
    assert seller.irn == "1234567890"
    assert seller.contact_phone == "+79001234567"
    assert seller.applications == []  # изначально заявок нет


def test_seller_submit_application():
    # Проверяет подачу заявки продавцом
    seller = Seller(
        id=str(uuid.uuid4()),
        full_name="Иван Петров",
        irn="1234567890",
        contact_phone="+79001234567",
    )

    app = seller.submit_application()

    # Заявка должна создаться и добавиться в список
    assert len(seller.applications) == 1
    assert seller.applications[0] == app
    assert app.seller_id == seller.id
    assert app.status == ApplicationStatus.NEW


def test_seller_upload_document():
    # Проверяет загрузку документа продавцом
    seller = Seller(
        id=str(uuid.uuid4()),
        full_name="Иван Петров",
        irn="1234567890",
        contact_phone="+79001234567",
    )
    app = seller.submit_application()
    doc_url = "https://docs.example.com/passport.pdf"

    seller.upload_document(app, doc_url)

    assert app.document_package_url == doc_url


# ТЕСТЫ APPLICATION


def test_application_creation():
    """Проверяет создание заявки."""
    seller_id = str(uuid.uuid4())
    app = Application(seller_id=seller_id)

    assert app.application_id is not None
    assert app.seller_id == seller_id
    assert app.status == ApplicationStatus.NEW
    assert app.document_package_url is None
    assert app.is_mercury_verified is False
    assert app.is_saturn_verified is False


def test_application_update_status():
    """Проверяет изменение статуса заявки."""
    app = Application(seller_id=str(uuid.uuid4()))

    app.update_status(ApplicationStatus.VERIFYING)
    assert app.status == ApplicationStatus.VERIFYING

    app.update_status(ApplicationStatus.APPROVED)
    assert app.status == ApplicationStatus.APPROVED


def test_application_validate_missing_docs():
    """Заявка невалидна без документов."""
    app = Application(seller_id=str(uuid.uuid4()))
    app.is_mercury_verified = True
    app.is_saturn_verified = True
    # Нет document_package_url

    assert app.validate() is False


def test_application_validate_missing_mercury():
    """Заявка невалидна без верификации Меркурия."""
    app = Application(seller_id=str(uuid.uuid4()))
    app.document_package_url = "https://docs.example.com/doc.pdf"
    app.is_saturn_verified = True
    # is_mercury_verified = False

    assert app.validate() is False


def test_application_validate_missing_saturn():
    """Заявка невалидна без верификации Сатурна."""
    app = Application(seller_id=str(uuid.uuid4()))
    app.document_package_url = "https://docs.example.com/doc.pdf"
    app.is_mercury_verified = True
    # is_saturn_verified = False

    assert app.validate() is False


def test_application_validate_all_ok():
    """Заявка валидна когда всё заполнено."""
    app = Application(seller_id=str(uuid.uuid4()))
    app.document_package_url = "https://docs.example.com/doc.pdf"
    app.is_mercury_verified = True
    app.is_saturn_verified = True

    assert app.validate() is True


# ==================== ТЕСТЫ TRADING POINT ====================


def test_trading_point_creation():
    """Проверяет создание торговой точки."""
    point = TradingPoint(point_id=1, zone_name="Мясной ряд", square_meters=15.5)

    assert point.point_id == 1
    assert point.zone_name == "Мясной ряд"
    assert point.square_meters == 15.5
    assert point.is_occupied is False
    assert point.assigned_seller_id is None


def test_trading_point_calculate_rent():
    """Проверяет расчёт арендной платы."""
    point = TradingPoint(point_id=1, zone_name="Овощной ряд", square_meters=10.0)

    # 10 кв.м × 1500 руб/кв.м = 15000
    expected_rent = 10.0 * 1500.0
    assert point.calculate_rent() == expected_rent


def test_trading_point_assign_seller():
    """Проверяет назначение продавца на точку."""
    point = TradingPoint(point_id=1, zone_name="Молочный ряд", square_meters=8.0)
    seller_id = str(uuid.uuid4())

    point.assign_seller(seller_id)

    assert point.is_occupied is True
    assert point.assigned_seller_id == seller_id


# ==================== ТЕСТЫ MARKET ADMIN ====================


def test_admin_review_approved_application():
    """Администратор одобряет полностью готовую заявку."""
    admin = MarketAdmin(admin_id=str(uuid.uuid4()), department="Отдел контроля")
    app = Application(seller_id=str(uuid.uuid4()))
    app.document_package_url = "https://docs.example.com/doc.pdf"
    app.is_mercury_verified = True
    app.is_saturn_verified = True

    result = admin.review_application(app)

    assert result is True
    assert app.status == ApplicationStatus.APPROVED


def test_admin_review_rejected_application():
    """Администратор отклоняет неготовую заявку."""
    admin = MarketAdmin(admin_id=str(uuid.uuid4()), department="Отдел контроля")
    app = Application(seller_id=str(uuid.uuid4()))
    # Ничего не заполнено

    result = admin.review_application(app)

    assert result is False
    assert app.status == ApplicationStatus.REJECTED


def test_admin_assign_free_trading_point():
    """Администратор назначает свободную точку продавцу."""
    admin = MarketAdmin(admin_id=str(uuid.uuid4()), department="Отдел контроля")
    seller = Seller(
        id=str(uuid.uuid4()),
        full_name="Иван Петров",
        irn="1234567890",
        contact_phone="+79001234567",
    )
    point = TradingPoint(point_id=1, zone_name="Мясной ряд", square_meters=12.0)

    admin.assign_trading_point(seller, point)

    assert point.is_occupied is True
    assert point.assigned_seller_id == seller.id


def test_admin_assign_occupied_trading_point():
    """Администратор не может назначить уже занятую точку."""
    admin = MarketAdmin(admin_id=str(uuid.uuid4()), department="Отдел контроля")
    seller1 = Seller(
        id=str(uuid.uuid4()),
        full_name="Иван Петров",
        irn="1234567890",
        contact_phone="+79001234567",
    )
    seller2 = Seller(
        id=str(uuid.uuid4()),
        full_name="Петр Иванов",
        irn="0987654321",
        contact_phone="+79007654321",
    )
    point = TradingPoint(point_id=1, zone_name="Мясной ряд", square_meters=12.0)

    # Первый продавец занимает точку
    admin.assign_trading_point(seller1, point)

    # Второй продавец пытается занять ту же точку — ошибка
    with pytest.raises(ValueError, match="уже занята"):
        admin.assign_trading_point(seller2, point)


# ==================== ТЕСТЫ FGIS MERCURY SYNC ====================


def test_mercury_send_vet_passport_with_docs():
    """Меркурий принимает документы, если они загружены."""
    mercury = FGIS_Mercury_Sync()
    app = Application(seller_id=str(uuid.uuid4()))
    app.document_package_url = "https://docs.example.com/doc.pdf"

    result = mercury.send_vet_passport(app)

    assert result is True
    assert app.is_mercury_verified is True
    assert mercury.status_response == "Vet passport accepted"
    assert mercury.last_update is not None


def test_mercury_send_vet_passport_without_docs():
    """Меркурий отклоняет, если документов нет."""
    mercury = FGIS_Mercury_Sync()
    app = Application(seller_id=str(uuid.uuid4()))
    # document_package_url = None

    result = mercury.send_vet_passport(app)

    assert result is False
    assert app.is_mercury_verified is False
    assert mercury.status_response == "No documents"


def test_mercury_check_certification_after_success():
    """Проверка сертификации после успешной отправки."""
    mercury = FGIS_Mercury_Sync()
    app = Application(seller_id=str(uuid.uuid4()))
    app.document_package_url = "https://docs.example.com/doc.pdf"
    mercury.send_vet_passport(app)  # сначала отправляем

    result = mercury.check_certification(app)

    assert result is True
    assert mercury.status_response == "Certification OK"


def test_mercury_check_certification_without_send():
    """Проверка сертификации без предварительной отправки."""
    mercury = FGIS_Mercury_Sync()
    app = Application(seller_id=str(uuid.uuid4()))

    result = mercury.check_certification(app)

    assert result is False
    assert mercury.status_response == "Certification failed"


# ==================== ТЕСТЫ FGIS SATURN SYNC ====================


def test_saturn_send_report_success():
    """Сатурн принимает отчёт, если всё готово."""
    saturn = FGIS_Saturn_Sync()
    app = Application(seller_id=str(uuid.uuid4()))
    app.document_package_url = "https://docs.example.com/doc.pdf"
    app.is_mercury_verified = True

    result = saturn.send_pesticide_report(app)

    assert result is True
    assert app.is_saturn_verified is True
    assert saturn.last_update is not None


def test_saturn_send_report_missing_docs():
    """Сатурн отклоняет отчёт без документов."""
    saturn = FGIS_Saturn_Sync()
    app = Application(seller_id=str(uuid.uuid4()))
    app.is_mercury_verified = True
    # document_package_url = None

    result = saturn.send_pesticide_report(app)

    assert result is False
    assert app.is_saturn_verified is False


def test_saturn_send_report_missing_mercury():
    """Сатурн отклоняет отчёт без верификации Меркурия."""
    saturn = FGIS_Saturn_Sync()
    app = Application(seller_id=str(uuid.uuid4()))
    app.document_package_url = "https://docs.example.com/doc.pdf"
    # is_mercury_verified = False

    result = saturn.send_pesticide_report(app)

    assert result is False


# ==================== ИНТЕГРАЦИОННЫЙ ТЕСТ ====================


def test_full_workflow():
    """Полный сценарий: от подачи заявки до назначения точки."""
    # Создаём участников
    seller = Seller(
        id=str(uuid.uuid4()),
        full_name="Фермер Олег",
        irn="7701234567",
        contact_phone="+79001112233",
    )
    admin = MarketAdmin(admin_id=str(uuid.uuid4()), department="Отдел контроля")
    point = TradingPoint(point_id=1, zone_name="Мясной ряд", square_meters=12.5)
    mercury = FGIS_Mercury_Sync()
    saturn = FGIS_Saturn_Sync()

    # 1. Подача заявки
    app = seller.submit_application()
    assert app.status == ApplicationStatus.NEW

    # 2. Загрузка документов
    seller.upload_document(app, "https://docs.example.com/doc.pdf")
    assert app.document_package_url is not None

    # 3. Проверка Меркурия
    mercury.send_vet_passport(app)
    mercury.check_certification(app)
    assert app.is_mercury_verified is True

    # 4. Отправка отчёта в Сатурн
    saturn.send_pesticide_report(app)
    assert app.is_saturn_verified is True

    # 5. Заявка готова к проверке
    assert app.validate() is True

    # 6. Администратор одобряет
    result = admin.review_application(app)
    assert result is True
    assert app.status == ApplicationStatus.APPROVED

    # 7. Назначение торговой точки
    admin.assign_trading_point(seller, point)
    assert point.is_occupied is True
    assert point.assigned_seller_id == seller.id

    # 8. Проверка арендной платы
    rent = point.calculate_rent()
    assert rent == 12.5 * 1500.0  # 18750.0
