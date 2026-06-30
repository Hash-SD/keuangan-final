import os


SECRET_KEY = os.environ.get("SUPERSET_SECRET_KEY", "change_this_secret")
SQLALCHEMY_DATABASE_URI = "sqlite:////app/superset_home/superset.db"
SQLALCHEMY_ENGINE_OPTIONS = {
    "connect_args": {"check_same_thread": False},
}
FEATURE_FLAGS = {
    "ENABLE_TEMPLATE_PROCESSING": True,
}
