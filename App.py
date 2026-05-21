from datetime import datetime
import uuid


class ApplicationStatus:
    # Статусы заявки
    NEW = "NEW"
    VERIFYING = "VERIFYING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class Application:
    # Представляет заявку продавца

    def __init__(self, seller_id):
        self.application_id = uuid.uuid4()
        self.created_at = datetime.now()
        self.status = ApplicationStatus.NEW
        self.seller_id = seller_id
        self.document_package_url = None
        self.is_mercury_verified = False

    def validate(self):
        """
        Проверяет, может ли заявка быть одобрена.

        Returns:
            bool: True, если документы загружены и верификация пройдена.
        """
        return bool(self.document_package_url and self.is_mercury_verified)

    def update_status(self, new_status):
        """
        Обновляет статус заявки.

        Args:
            new_status (str): Новый статус заявки.
        """
        self.status = new_status
        print(
            f"[Application] Статус заявки {self.application_id} "
            f"изменен на: {new_status}"
        )


class Seller:
    # Представляет продавца

    def __init__(self, id, name, inn, phone):
        self.id = id
        self.name = name
        self.inn = inn
        self.phone = phone
        self.applications = []

    def submit_application(self):
        """
        Создаёт новую заявку для продавца.

        Returns:
            Application: Новая заявка.
        """
        new_app = Application(seller_id=self.id)
        self.applications.append(new_app)
        print(
            f"[Seller] {self.name} подал новую заявку {new_app.application_id}"
        )
        return new_app

    def upload_document(self, app, url):
        """
        Загружает документы по ссылке.

        Args:
            app (Application): Заявка.
            url (str): Ссылка на документы.
        """
        app.document_package_url = url
        print(f"[Seller] Документы загружены по адресу: {url}")


class MarketAdmin:
    # Представляет администратора маркетплейса

    def __init__(self, admin_id, department):
        self.admin_id = admin_id
        self.department = department

    def review_application(self, app):
        """
        Проверяет заявку и выносит решение.

        Args:
            app (Application): Заявка для проверки.

        Returns:
            bool: True, если заявка одобрена.
        """
        print(f"[Admin] Рассмотрение заявки {app.application_id}...")
        if app.validate():
            app.update_status(ApplicationStatus.APPROVED)
            return True
        else:
            app.update_status(ApplicationStatus.REJECTED)
            return False

if __name__ == "__main__":
    # Инициализация участников
    seller = Seller(
        id=uuid.uuid4(),
        name="Фермер Олег",
        inn="7701234567",
        phone="+79001112233"
    )
    admin = MarketAdmin(admin_id=uuid.uuid4(), department="Отдел контроля")

    # Подача заявки
    my_app = seller.submit_application()
    seller.upload_document(
        my_app,
        "https://cloud.market.ru/docs/id_01.pdf"
    )

    # Имитация верификации в Меркурии
    my_app.is_mercury_verified = True

    # Проверка администратором
    admin.review_application(my_app)
