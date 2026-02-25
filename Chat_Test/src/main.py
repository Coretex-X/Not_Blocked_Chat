import flet as ft
import json as js
import sqlite3 as ql
import requests as rq
from app.menu import main_menu
from app.settings import settings_view
from app.registration import main_registartion
from app.sign_up import main_sign_up
import path

db_path = f'{path.db_path()}user_data.db'

with ql.connect(db_path) as con:
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users_data(
        id_user TEXT,
        name TEXT,
        profile TEXT,
        PRIMARY KEY (access_token)
        );
        """)
    cur.close()

#rq.post("http://localhost:5000/api/v2/user/sesion/", json={"action": 'online'})

def main(page: ft.Page):
    def route_change(route):
        page.views.clear()
        page.views.append(
            main_menu(page)
            )

        if page.route == "/settings":
            page.views.append(
                settings_view(page)
            )


        elif page.route == "/registration":
            page.views.append(
                main_registartion(page)
            )

        elif page.route == "/login":
           page.views.append(
                main_sign_up(page)
            )

        page.update()

    def view_pop(view):
        page.views.pop()
        top_view = page.views[-1]
        page.go(top_view.route)

    page.on_route_change = route_change
    #page.on_view_pop = view_pop
    page.go(page.route)

ft.app(target=main, view=ft.WEB_BROWSER, port=8080)
#ft.app(main)