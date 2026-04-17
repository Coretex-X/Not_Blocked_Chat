import flet as ft
import sqlite3 as sql
import json as js
import path

db_path = f"{path.db_path()}user_data.db"

def settings_view(page):

    with sql.connect(db_path) as con:
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

    def edit_profile(e):
       print(f'Hello {e}')


    '''def toggle_theme(e):
        # Сначала меняем тему в данных
        if data["theme"] == 'light':
            data_theme_dark = {'theme':'dark'}
            with open('/home/archlinux05/Chat_Test/src/config/config.jsonc', 'w', encoding='utf-8') as file:
                js.dump(data_theme_dark)
        else:
            data_theme_light = {'theme':'light'}
            with open('/home/archlinux05/Chat_Test/src/config/config.jsonc', 'w', encoding='utf-8') as file:
                js.dump(data_theme_light)
        
        # Применяем новую тему к странице
        page.theme_mode = data["theme"]
        
        # Сохраняем изменения в файл
        try:
            with open('/home/archlinux05/Chat_Test/src/config/config.jsonc', 'w', encoding='utf-8') as f:
                js.dump(data, f, indent=4, ensure_ascii=False)  # ensure_ascii=False для кириллицы
        except Exception as e:
            print(f"Ошибка при сохранении темы: {e}")
        
        # Обновляем страницу
        page.update()'''

    profile_header = ft.Container(
    content=ft.Container(
        content=ft.Column(
                    controls=[
                        ft.CircleAvatar(
                            foreground_image_src='/home/archlinux05/ChatApp/TestServerApp/media/images/Z.png',
                            radius=50,
                        ),
                        ft.Text(
                            user_name[0], 
                            weight="bold", 
                            size=25,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        ft.Text(
                            "None",
                            size=17,
                            color="grey",
                            text_align=ft.TextAlign.CENTER,
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=10,
                ),
                width=250,
                alignment=ft.alignment.center,
            ),
            alignment=ft.alignment.center,
            expand=True,  # Занимает все доступное пространство
            on_click=lambda e: edit_profile(page),
        )
            
    # Разделы настроек
    settings_options = [
        {"icon": ft.Icons.ACCOUNT_CIRCLE, "title": "Аккаунт",},
        {"icon": ft.Icons.CHAT, "title": "Чаты", },
        {"icon": ft.Icons.NOTIFICATIONS, "title": "Уведомления", },
        {"icon": ft.Icons.STORAGE, "title": "Хранилище и данные", },
        {"icon": ft.Icons.HELP, "title": "Помощь",},
        {"icon": ft.Icons.PEOPLE, "title": "Пригласить друзей",},
    ]
    
    # Создаем ListView с настройками
    settings_list = ft.ListView(expand=1, spacing=10)
    for option in settings_options:
        settings_list.controls.append(
            ft.ListTile(
                leading=ft.Icon(option["icon"]),
                title=ft.Text(option["title"]),
                #on_click=lambda e, action=option["action"]: action(page),
            )
        )
    
    # Собираем все вместе
    content = ft.Column(
            controls=[
                ft.Container(
                    content=profile_header,
                    padding=ft.padding.only(bottom=10)  # Уменьшаем отступ снизу
                ),
                ft.Divider(height=1),
                settings_list,
            ],
            expand=True,
            spacing=0,
    )

    theme_switch = ft.Switch(
        value=False,  # начальное положение (выключен)
        #on_change=toggle_theme,
        thumb_color=ft.Colors.WHITE,
        active_track_color=ft.Colors.BLUE_700,
        inactive_track_color=ft.Colors.GREY,
    )

    appbar = ft.AppBar(
        leading=ft.IconButton(ft.Icons.CHEVRON_LEFT, on_click=lambda _: page.go("/")),
        leading_width=40,
        title=ft.Text("Настройки"),
        center_title=False,
        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
    )
    
    return ft.View(
        "/settings",
        appbar=appbar,
        controls=[content, theme_switch],
    )