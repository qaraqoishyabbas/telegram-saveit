def pluralize_files(count):
    if count % 10 == 1 and count % 100 != 11:
        return "файл"
    if 2 <= count % 10 <= 4 and not 12 <= count % 100 <= 14:
        return "файла"
    return "файлов"
