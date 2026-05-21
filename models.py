from datetime import datetime
from enum import Enum
import uuid

class ApplicationStatus(str, Enum):
    NEW = "NEW"
    VERIFYING = "VERIFYING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class Application:
    def __init__(self, seller_id):
        self.application_id = uuid.uuid4()
        self.created_at = datetime.now()
        self.status = ApplicationStatus.NEW
        self.seller_id = seller_id
        self.document_package_url = None
        self.is_mercury_verified = False  # результат проверки Меркурия
        self.is_saturn_verified = False   # результат проверки Сатурна

    def validate(self):
        """Проверяет, готова ли заявка к одобрению."""
        return bool(
            self.document_package_url
            and self.is_mercury_verified
            and self.is_saturn_verified
        )

    def update_status(self, new_status: ApplicationStatus):
        self.status = new_status
        print(f"[Application] Статус заявки {self.application_id} изменён на {new_status}")


class Seller:
    def __init__(self, id, full_name, irn, contact_phone):
        self.id = id
        self.full_name = full_name
        self.irn = irn                  # идентификационный номер (ИНН)
        self.contact_phone = contact_phone
        self.applications = []

    def submit_application(self):
        app = Application(seller_id=self.id)
        self.applications.append(app)
        print(f"[Seller] {self.full_name} подал заявку {app.application_id}")
        return app

    def upload_document(self, app: Application, url: str):
        app.document_package_url = url
        print(f"[Seller] Документы загружены: {url}")


class TradingPoint:
    RENT_PER_SQM = 1500.0  # тариф за кв.м.

    def __init__(self, point_id: int, zone_name: str, square_meters: float):
        self.point_id = point_id
        self.zone_name = zone_name
        self.square_meters = square_meters
        self.is_occupied = False
        self.assigned_seller_id = None

    def calculate_rent(self) -> float:
        """Стоимость аренды = площадь × тариф."""
        return self.square_meters * self.RENT_PER_SQM

    def assign_seller(self, seller_id):
        self.is_occupied = True
        self.assigned_seller_id = seller_id


class MarketAdmin:
    def __init__(self, admin_id, department):
        self.admin_id = admin_id
        self.department = department

    def review_application(self, app: Application) -> bool:
        print(f"[Admin] Рассмотрение заявки {app.application_id}")
        if app.validate():
            app.update_status(ApplicationStatus.APPROVED)
            return True
        else:
            app.update_status(ApplicationStatus.REJECTED)
            return False

    def assign_trading_point(self, seller: Seller, point: TradingPoint):
        """Закрепляет свободную торговую точку за продавцом."""
        if point.is_occupied:
            raise ValueError(f"Точка {point.point_id} уже занята")
        point.assign_seller(seller.id)
        print(f"[Admin] Продавец {seller.full_name} получил точку {point.point_id} ({point.zone_name})")


class FGIS_Mercury_Sync:
    def __init__(self, sync_id=None):
        self.sync_id = sync_id or uuid.uuid4()
        self.last_update = None
        self.status_response = ""

    def send_vet_passport(self, app: Application) -> bool:
        """Эмуляция отправки ветпаспорта. Возвращает True при успехе."""
        self.last_update = datetime.now()
        # Имитация успешной отправки, если документы загружены
        if app.document_package_url:
            self.status_response = "Vet passport accepted"
            app.is_mercury_verified = True
            print(f"[Mercury] Ветпаспорт по заявке {app.application_id} отправлен")
            return True
        self.status_response = "No documents"
        return False

    def check_certification(self, app: Application) -> bool:
        """Эмуляция проверки сертификации. Возвращает True, если Меркурий подтвердил."""
        # Зависит от предыдущей отправки
        if app.is_mercury_verified:
            self.status_response = "Certification OK"
            return True
        self.status_response = "Certification failed"
        return False


class FGIS_Saturn_Sync:
    def __init__(self, sync_id=None):
        self.sync_id = sync_id or uuid.uuid4()
        self.last_update = None

    def send_pesticide_report(self, app: Application) -> bool:
        """Эмуляция отправки отчёта о пестицидах."""
        self.last_update = datetime.now()
        # Успех, если документы загружены и Меркурий пройден (пример зависимости)
        if app.document_package_url and app.is_mercury_verified:
            app.is_saturn_verified = True
            print(f"[Saturn] Отчёт по заявке {app.application_id} отправлен")
            return True
        print(f"[Saturn] Отчёт по заявке {app.application_id} не принят")
        return False
    