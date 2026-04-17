from datetime import datetime


# Таблица транслитерации кириллицы
_CYR_TO_LAT = {
    'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D',
    'Е': 'E', 'Ё': 'E', 'Ж': 'Z', 'З': 'Z', 'И': 'I',
    'Й': 'I', 'К': 'K', 'Л': 'L', 'М': 'M', 'Н': 'N',
    'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T',
    'У': 'U', 'Ф': 'F', 'Х': 'H', 'Ц': 'C', 'Ч': 'C',
    'Ш': 'S', 'Щ': 'S', 'Ъ': '', 'Ы': 'Y', 'Ь': '',
    'Э': 'E', 'Ю': 'U', 'Я': 'Y',
}


def format_phone(number: str) -> str:
    """Форматирует номер телефона в вид +7 (XXX) XXX-XX-XX."""
    if not number:
        return ""
    digits = ''.join(filter(str.isdigit, str(number)))
    if len(digits) == 11:
        digits = digits[1:]
    if len(digits) == 10:
        return f"+7 ({digits[0:3]}) {digits[3:6]}-{digits[6:8]}-{digits[8:10]}"
    return str(number)


def get_avatar_letter(name: str) -> str:
    """Возвращает латинскую букву для аватара по первому символу имени."""
    if not name:
        return "U"
    ch = name[0].upper()
    return _CYR_TO_LAT.get(ch, ch if ch.isalpha() else 'U')


def format_chat_time(time_string: str) -> str:
    """Форматирует строку даты-времени в HH:MM."""
    if not time_string:
        return ""
    try:
        fmt = '%Y-%m-%d %H:%M:%S.%f' if '.' in time_string else '%Y-%m-%d %H:%M:%S'
        return datetime.strptime(time_string, fmt).strftime('%H:%M')
    except ValueError:
        return ""
