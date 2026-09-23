"""Safe Child — Child Safety Pakistan.

One app, two modules:
  1. Adaptive behavioral screening (rule-based expert system, NOT ML)
  2. Formal abuse-report filing with case-file generation

100% Python (Reflex). No handwritten JavaScript.
"""

import reflex as rx

from safe_child import app as app_module  # noqa: F401  (State + views)


app = rx.App(
    head_components=[
        rx.el.link(
            rel="stylesheet",
            href="https://fonts.googleapis.com/css2?family=Noto+Nastaliq+Urdu:wght@400;600;700&display=swap",
        ),
        rx.el.link(rel="manifest", href="/manifest.webmanifest"),
        rx.el.meta(name="theme-color", content="#2AA89B"),
        rx.el.link(
            rel="icon",
            href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'><rect width='64' height='64' rx='14' fill='%232AA89B'/><path d='M32 12l14 5v10c0 9-6 16-14 19-8-3-14-10-14-19V17z' fill='white'/><path d='M26 32l5 5 11-11' stroke='%232AA89B' stroke-width='4' fill='none' stroke-linecap='round'/></svg>",
        ),
    ],
    stylesheets=["/style.css"],
)

app.add_page(app_module.index, route="/", title="Safe Child — Child Safety Pakistan")
