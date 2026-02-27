import flet as ft
import sqlite3 as sql 
import json as js
import os
##########################################################################################################################################################################
#with open('/home/username/Test/ChatApp/Chat_Test/src/config/config.jsonc', 'r', encoding='utf-8') as file:
 #   data = js.load(file)
##########################################################################################################################################################################
def main_menu(page):
    page.title = 'AppChat'
    #page.theme_mode = data["theme"]
    user_profil = 'None'
##########################################################################################################################################################################
    with sql.connect("/home/username/Test/Test_Chat/Chat_Test/src/data/user_data.db") as con:
        cur = con.cursor()
        try:
            cur.execute("SELECT name, profile FROM users_data")
        except sql.OperationalError:
            pass
        result = cur.fetchall()
    cur.close()
    try:
        user_name = result[0]
    except IndexError:
        user_name = 'None'
##########################################################################################################################################################################
    def get_out(e):
        os.remove('/home/archlinux05/Chat_Test/src/data/user_data.db')
        #data["is_authenticated"] == None
        #with open('/home/archlinux05/Chat_Test/src/config/config.jsonc', 'w') as f:
            #js.dump(data, f, indent=4)
        page.go('/login')
        dlg.open = False
        page.update()
##########################################################################################################################################################################
    def new_chat(e):
        pass
    def new_groop(e):
        pass
    def chat_ai(e):
        pass
    def calls(e):
        pass
##########################################################################################################################################################################
    def close_dialog(e):
        dlg.open = False
        page.update()
##########################################################################################################################################################################
    def open_dialog(e):
        page.dialog = dlg
        dlg.open = True
        page.update()
##########################################################################################################################################################################
    dlg = ft.AlertDialog(
            title=ft.Text("Вы уверены что хотите выйти?"),
            content=ft.Text("Подтвердите выполнение действия"),
            actions=[
                ft.TextButton("Да", on_click=get_out),
                ft.TextButton("Нет", on_click=close_dialog),
            ],
        )
##########################################################################################################################################################################
    appbar = ft.AppBar(
        adaptive=True,
        leading=ft.Icon(ft.Icons.CHAT),
        leading_width=40,
        title=ft.Text("AppChat"),
        center_title=False,
        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
        actions=[
            ft.PopupMenuButton(
            items=[
                ft.PopupMenuItem(
                        content=ft.Container(
                            content=ft.Column(
                                controls=[
                                    ft.CircleAvatar(
                                        foreground_image_src='/home/archlinux05/ChatApp/TestServerApp/media/images/Z.png',  # Используйте URL вместо локального пути
                                        radius=40,
                                    ),
                                    ft.Text(
                                        user_name[0], 
                                        weight="bold", 
                                        size=20,
                                        text_align=ft.TextAlign.CENTER,  # Центрируем текст
                                        width=200  # Фиксированная ширина для выравнивания
                                    ),
                                    ft.Text(
                                        user_profil,
                                        size=12,
                                        color="grey",
                                        text_align=ft.TextAlign.CENTER,
                                        width=200
                                    ),
                                ],
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                spacing=10,
                            ),
                            padding=ft.padding.symmetric(vertical=10),
                            alignment=ft.alignment.center,  # Двойное центрирование
                            width=250,  # Фиксированная ширина контейнера
                        )
                    ),
                ft.PopupMenuItem(),  # Разделитель (пустая строка)
                ft.PopupMenuItem(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.PLUS_ONE_ROUNDED, size=20),
                            ft.Text('Новый чат'),
                        ],
                        spacing=10,
                    ),
                    on_click=new_chat
                ),
                ft.PopupMenuItem(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.CHAT_ROUNDED, size=20),
                            ft.Text('Новый Група'),
                        ],
                        spacing=10,
                    ),
                    on_click=new_groop,
                ),
                ft.PopupMenuItem(
                    content=ft.Row(
                        controls=[
                            #ft.Icon(ft.Icons.PLUS_ONE_ROUNDED, size=20),
                            ft.Text('Чат с IA'),
                        ],
                        spacing=10,
                    ),
                    on_click=chat_ai
                ),
                ft.PopupMenuItem(),
                ft.PopupMenuItem(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.DATA_SAVER_OFF, size=20),
                            ft.Text("Cтатус"),
                        ],
                        spacing=10,
                    ),
                    on_click= lambda _: page.go('/status')
                ),
                ft.PopupMenuItem(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.CALL, size=20),
                            ft.Text("Звонки"),
                        ],
                        spacing=10,
                    ),
                    on_click=calls
                ),
                ft.PopupMenuItem(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.SETTINGS_OUTLINED, size=20),
                            ft.Text("Настройки"),
                        ],
                        spacing=10,
                    ),
                    on_click= lambda _: page.go('/settings')
                ),
                ft.PopupMenuItem(),
                ft.PopupMenuItem(
                    content=ft.Row(
                        controls=[
                            ft.Text("Войти"),
                            ft.Icon(ft.Icons.LOGIN, size=20)
                        ],
                        spacing=10,
                    ),
                    on_click = lambda _: page.go('/login'),
                ),
                ft.PopupMenuItem(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.LOGIN, size=20),
                            ft.Text("Выйти"),
                        ],
                        spacing=10,
                    ),
                    on_click = open_dialog,
                ),
            ]
        )
        ],
    )
##########################################################################################################################################################################
    tabs = ft.Tabs(
        adaptive=True,
        selected_index=1,
        animation_duration=300,
        tabs=[
            ft.Tab(
                text="Все",
                content=ft.Container(
                    content=ft.Text("Здесь пока что ничего нет!"), 
                    alignment=ft.alignment.center,
                ),
            ),
            ft.Tab(
                text='Избранное',
                content=ft.Container(
                    content=ft.Text("Здесь пока что ничего нет!"), 
                    alignment=ft.alignment.center
                ),
            ),
            ft.Tab(
                text="Группы",
                content=ft.Container(
                    content=ft.Text("Здесь пока что ничего нет!"), 
                    alignment=ft.alignment.center
                ),
            ),
        ],
        expand=1,
    )
########################################################################################################################################################################## 
    return ft.View(
        "/",
        [tabs, dlg],
        appbar=appbar,
        #navigation_bar=navigation_bar
    )
