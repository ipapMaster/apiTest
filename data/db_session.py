import sqlalchemy as sa
import sqlalchemy.orm as orm
from sqlalchemy.orm import Session, declarative_base
from typing import Optional

SqlAlchemyBase = declarative_base()


class SessionManager:
    """Singleton-класс для управления сессиями SQLAlchemy."""

    _instance: Optional["SessionManager"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SessionManager, cls).__new__(cls)
            cls._instance._session_factory = None
        return cls._instance

    def global_init(self, db_file: str) -> None:
        """Инициализация подключения к базе данных."""
        if self._session_factory is not None:
            return

        db_file = db_file.strip()
        if not db_file:
            raise ValueError("Необходимо указать путь к файлу базы данных.")

        conn_str = f"sqlite:///{db_file}?check_same_thread=False"
        print(f"[INFO] Подключение к базе данных: {conn_str}")

        engine = sa.create_engine(conn_str, echo=False)
        self._session_factory = orm.sessionmaker(bind=engine)

        from . import db_models  # noqa: F401
        SqlAlchemyBase.metadata.create_all(engine)

    def create_session(self) -> Session:
        """Создание новой сессии."""
        if self._session_factory is None:
            raise RuntimeError("Session factory не инициализирован. Вызовите global_init() сначала.")
        return self._session_factory()


# Экземпляр-синглтон
session_manager = SessionManager()
