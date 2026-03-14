#def db_path():
#    path_user = '/home/archlinux05/Home/Test/Not Blocked Chat/Client/src/assets/data/'
#    #path_user = '/home/username/Test/Test_Chat/ChatTest/Chat_Test/src/data/'
#    return path_user
import os
from pathlib import Path
import sys

def db_path():
    """
    Возвращает правильный путь к директории с данными
    для Linux и Android
    """
    # Определяем, запущены ли мы на Android
    if 'ANDROID_ARGUMENT' in os.environ or 'ANDROID_ROOT' in os.environ:
        # Для Android используем директорию приложения
        # Получаем путь к директории, где находится наше приложение
        if getattr(sys, 'frozen', False):
            # Если приложение скомпилировано в APK
            base_path = Path(sys.executable).parent
        else:
            # Если запущено как скрипт
            base_path = Path(__file__).parent.parent.parent
        
        # Создаём путь к папке данных внутри приложения
        data_path = base_path / 'data'
        
        # Убеждаемся, что папка существует
        data_path.mkdir(parents=True, exist_ok=True)
        
        return str(data_path) + '/'
    
    else:
        # Для Linux (ваш оригинальный путь)
        return '/home/archlinux05/Home/Test/Not Blocked Chat/Client/src/assets/data/'

# Для удобства можно создать переменную при импорте
DATA_PATH = db_path()