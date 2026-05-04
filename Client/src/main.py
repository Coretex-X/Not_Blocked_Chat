import flet as ft
import sqlite3 as ql
import path
from app.menu import main_menu
from app.settings import settings_view
from app.registration import main_registartion
from app.sign_up import main_sign_up
from app.chat import chat_view

db_path = f"{path.db_path()}user_data.db"

# Создаём таблицы при первом запуске
with ql.connect(db_path) as con:
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users_data(
            id_user INTEGER,
            name TEXT,
            profile TEXT,
            number TEXT,
            token TEXT,
            avatar TEXT)
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_settings(
            authorization TEXT DEFAULT 'false',
            color_theme TEXT DEFAULT 'light',
            language TEXT DEFAULT 'ru'
        )
    """)

with ql.connect(db_path) as con:
    cur = con.cursor()
    cur.execute("SELECT authorization FROM user_settings LIMIT 1")
    row = cur.fetchone()
    is_authorized = (row[0] if row else 'false') == 'true'


def main(page: ft.Page):
    def route_change(route):
        page.views.clear()
        page.views.append(main_menu(page))

        if not is_authorized:
            page.views.append(main_sign_up(page))

        if page.route == "/main":
            page.views.append(main_menu(page))
        elif page.route == "/settings":
            page.views.append(settings_view(page))
        elif page.route == "/registration":
            page.views.append(main_registartion(page))
        elif page.route == "/login":
            page.views.append(main_sign_up(page))
        elif page.route == "/chat":
            page.views.append(chat_view(page))

        page.update()

    def view_pop(view):
        page.views.pop()
        page.go(page.views[-1].route)

    page.on_route_change = route_change
    page.go(page.route)


ft.app(main)
