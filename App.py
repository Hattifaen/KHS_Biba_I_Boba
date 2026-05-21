from datetime import datetime
import uuid

class ApplicationStatus:
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
        self.is_mercury_verified = False

    def validate(self):
        # Простая проверка: есть ли документы и пройдена ли внешняя проверка
        if self.document_package_url and self.is_mercury_verified:
            return True
        return False

    def update_status(self, new_status):
        self.status = new_status
        print(f"[Application] Статус заявки {self.application_id} изменен на: {new_status}")

class Seller:
    def __init__(self, id, name, inn, phone):
        self.id = id
        self.name = name
        self.inn = inn
        self.phone = phone
        self.applications = []

    def submit_application(self):
        # Создаем новую заявку и привязываем её к продавцу
        new_app = Application(seller_id=self.id)
        self.applications.append(new_app)
        print(f"[Seller] {self.name} подал новую заявку {new_app.application_id}")
        return new_app

    def upload_document(self, app, url):
        app.document_package_url = url
        print(f"[Seller] Документы загружены по адресу: {url}")

class MarketAdmin:
    def __init__(self, admin_id, department):
        self.admin_id = admin_id
        self.department = department

    def review_application(self, app):
        print(f"[Admin] Рассмотрение заявки {app.application_id}...")
        if app.validate():
            app.update_status(ApplicationStatus.APPROVED)
            return True
        else:
            app.update_status(ApplicationStatus.REJECTED)
            return False

# --- Пример работы системы ---

# 1. Инициализация участников
seller = Seller(id=uuid.uuid4(), name="Фермер Олег", inn="7701234567", phone="+79001112233")
admin = MarketAdmin(admin_id=uuid.uuid4(), department="Отдел контроля")

# 2. Процесс подачи заявки
my_app = seller.submit_application()
seller.upload_document(my_app, "https://cloud.market.ru/docs/id_01.pdf")

# 3. Имитация внешней проверки (ФГИС Меркурий)
# В реальности это делает отдельный модуль интеграции
my_app.is_mercury_verified = True 

# 4. Проверка администратором
admin.review_application(my_app)