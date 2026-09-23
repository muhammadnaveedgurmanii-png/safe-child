import reflex as rx

config = rx.Config(
    app_name="safe_child",
    frontend_port=3000,
    backend_port=8000,
    api_url="http://localhost:8000",
    deploy_url=None,
    show_built_with_reflex=False,
)
