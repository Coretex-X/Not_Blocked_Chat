import flet as ft
import sqlite3 as ql
from app.menu import main_menu
from app.settings import settings_view
from app.registration import main_registartion
from app.sign_up import main_sign_up
from app.chat import chat_view
import path
import os

db_path = f'{path.db_path()}user_data.db'

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
    cur.close()

def main(page: ft.Page):
    def route_change(route):
        page.views.clear()

        is_logged_in = False
        if os.path.exists(db_path):
            try:
                with ql.connect(db_path) as con:
                    cur = con.cursor()
                    cur.execute("SELECT COUNT(*) FROM users_data")
                    is_logged_in = cur.fetchone()[0] > 0
            except:
                pass

        # Если не авторизован — только страницы входа
        if not is_logged_in and page.route not in ["/login", "/registration"]:
            page.views.append(main_sign_up(page))
            page.update()
            return


        if page.route == "/login":
            page.views.append(main_sign_up(page))

        elif page.route == "/registration":
            page.views.append(main_registartion(page))

        elif page.route == "/settings":
            page.views.append(main_menu(page))
            page.views.append(settings_view(page))

        elif page.route == "/chat":
            page.views.append(main_menu(page))
            page.views.append(chat_view(page))

        else:  # "/"
            page.views.append(main_menu(page))

        page.update()

    def view_pop(view):
        if len(page.views) > 1:
            page.views.pop()
            top_view = page.views[-1]
            page.go(top_view.route)
        else:
            page.go("/")

    page.on_route_change = route_change
    page.on_view_pop = view_pop
    page.go(page.route)

ft.app(target=main)