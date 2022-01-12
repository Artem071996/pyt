import sqlite3

def seve(name_user,
         id_line,
         user_id,
         user_command,
         time,
         user_request_city,
         user_count_hotels,
         user_answer_photo,
         user_count_photo,
         user_min_price,
         user_max_price,
         user_min_distance,
         history_hotels):
    with sqlite3.connect('history.db') as db:  # открываем файл для хранения базы данных

        cursor = db.cursor()  # определяем курсор
        query = f""" CREATE TABLE IF NOT EXISTS {name_user}(
                id_line TEXT,
                id TEXT,
                команды TEXT,
                время TEXT,
                город TEXT,
                количество_отелей TEXT,
                вывод_фото TEXT,
                количество_фото TEXT,
                минимальная_стоимость TEXT,
                максимальная_стоимость TEXT,
                минимальное_расстояние TEXT,
                отели TEXT)"""

        albums = [(id_line,
                   user_id,
                   user_command,
                   time,
                   user_request_city,
                   user_count_hotels,
                   user_answer_photo,
                   user_count_photo,
                   user_min_price,
                   user_max_price,
                   user_min_distance,
                   history_hotels)]

        cursor.execute(query)  # добавляем столбцы
        db.commit()  # сохраняем
        cursor.executemany(f"INSERT INTO {name_user} VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", albums)  # добавляем строки
        db.commit()  # сохраняем
