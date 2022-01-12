import os  # библиотека для работы с операционной системой
import time  # библиотека для работы с временем
import re  # библиотека для работы с регулярными выражениями

from dotenv import load_dotenv  # библиотека для получения ТОКЕНА и ЮРЛ адресов сайта
from telebot import TeleBot, \
    types  # библиотека для работы бота, общения, обработки сообщений и библиотека дл реализации кнопок

import sqlite3  # библиотека, для работы с sql таблицами
from loguru import logger  # библиотека для логирования ошибок
from telegram_bot_calendar import DetailedTelegramCalendar, LSTEP  # библиотека для создания календаря

from user import Users  # импортированный класс пользователя, для записи и получения необходимых данных
from botrequests import lowprice, highprice, bestdeal  # импортированный файл для парсинга данных
import history  # импортированный файл, для работы с БД

import emoji  # билиотека для отправки смайлов

logger.add('debug.json', encoding='UTF-8', format='{time} {level} {message}',
           level='DEBUG')  # Логирование ошибок и исключений

load_dotenv()

token = os.getenv('TOKEN')  # импортируем токен из файла .env и присваиваем переменной, для дальнейшего использования

bot = TeleBot(token, parse_mode=None)  # инициализация бота

start_message = 'Список доступных команд:\n' \
                '/lowprice - самые дешевые отели в городе\n' \
                '/highprice - самые дорогие отели в городе\n' \
                '/bestdeal - отели наиболее подходящие по цене и расположению от центра города\n' \
                '/history - история поиска\n' \
                '/help - помощь по командам бота'

list_emoji = {'улыбка': emoji.emojize(':smiling_face_with_smiling_eyes:'),
              'грусть': emoji.emojize(':disappointed_face:'),
              'город': emoji.emojize(':cityscape:'),
              'цена': emoji.emojize(':dollar_banknote:'),
              'количество': emoji.emojize(':input_numbers:'),
              'фото': emoji.emojize(':framed_picture:'),
              'расстояние': emoji.emojize(':motorway:'),
              'вопрос': emoji.emojize(':exclamation_question_mark:'),
              'обработка': emoji.emojize(':hourglass_not_done:'),
              'поиск': emoji.emojize(':woman_detective:')}

list_commands = ['/lowprice', '/highprice', '/bestdeal', '/history',
                 '/help']  # список команд, для остановки бота и перехода в другой раздел

normal = "^[a-zA-Zа-яА-ЯёЁ]+$"  # разрешённые символы, при запросе поиска города


@bot.message_handler(commands=['start'])
def greetings(message):
    user = Users.get_user(message.chat.id, message.from_user.first_name, message.from_user.last_name)
    bot.send_message(user.chat_id,
                     f"{user.name_user} добро пожаловать {list_emoji['улыбка']}\nЯ бот Генадий, готов помочь тебе в подборе отелей")
    bot.send_message(user.chat_id, start_message)


@bot.message_handler(commands=['help'])
def greetings(message):
    user = Users.get_user(message.chat.id, message.from_user.first_name, message.from_user.last_name)
    bot.send_message(user.chat_id, 'Нужна помощь?\nВот список доступных команд:\n{}'.format(start_message))


@bot.message_handler(commands=['lowprice', 'highprice', 'bestdeal'])
def greetings(message):
    user = Users.get_user(message.chat.id, message.from_user.first_name, message.from_user.last_name)
    named_tuple = time.localtime()  # записываем время ввода команды
    user.user_command = message.text.replace('/', '')

    logger.debug(
        f"Пользователь: {user.name_user}, введена команда -  {user.user_command}")

    user.id_line += 1  # увеличиваем значение строки на 1( нужно для базы данных)
    user.time = time.strftime("%m/%d/%Y, %H:%M:%S", named_tuple)  # записываем время ввода команды
    bot.send_message(user.chat_id, f"Введите город, в котором будем искать отели {list_emoji['город']}")
    bot.register_next_step_handler(message, city_request)


@bot.message_handler(commands=['history'])
def greetings(message):
    user = Users.get_user(message.chat.id, message.from_user.first_name, message.from_user.last_name)
    logger.debug(
        f"Пользователь: {user.name_user}, запрос на выбор вывода истории поиска ")
    bot.send_message(user.chat_id,
                     'Введите 1 - для вывода всей истории поиска\nВведите 2 - для вывода последнего запроса')  # запрашиваем кол-во отелей
    bot.register_next_step_handler(message, get_history)


@bot.message_handler(content_types='text')  # Коллбэк, для обработки нажатия на кнопки выбора района в найденном городе
def message_reply(message):
    """
    Коллбэк, для обработки нажатия на кнопки выбора района в найденном городе
    А так же записи в класс пользователь выбранного района, айди района, координад района, для определения расстояния от центра до отеля
    :param message:сообщение от пользователя

    """

    user = Users.get_user(message.chat.id, message.from_user.first_name, message.from_user.last_name)
    user.city = message.text  # запись выбрнного района
    try:
        user.id_city = user.list_districts[message.text][0]  # запись айди выбранного района
        user.coordinates = user.list_districts[message.text][1], user.list_districts[message.text][
            2]  # запись координат выбранного города, для определения расстояния от центра до отеля

        bot.send_message(user.chat_id, f'Вы выбрали район: {message.text}',
                         reply_markup=types.ReplyKeyboardRemove(), parse_mode='Markdown')
        logger.debug(f"Пользователь: {user.name_user}, в веденном городе выбрал район - {user.city}")

        check_in_data(message)
    except BaseException as file:
        bot.send_message(user.chat_id,
                         f"Ошибка {list_emoji['грусть']}\nК сожалению я не понимаю вас\nВы должны выбрать из предложенных вариантов, а не писать мне в чат.")
        logger.debug(
            f'Ошибка, пользователь вводит текс, а необходимо выбрать из предложенных вариантов. Функция - requests_hotel_api, ошибки - {file}')


@bot.callback_query_handler(
    func=DetailedTelegramCalendar.func(calendar_id=1))  # Коллбэк, для обработки нажатия на кнопки выбора даты заезда
def cal1(call):
    """
        Коллбэк, для обработки нажатия на кнопки выбора даты заезда
        А так же записи в класс пользователь даты заезда
        :param call: сообщение от пользователя

        """

    user = Users.get_user(call.message.chat.id, call.message.chat.first_name, call.message.chat.last_name)
    result, key, step = DetailedTelegramCalendar(calendar_id=1, locale='ru').process(call.data)

    if not result and key:
        bot.edit_message_text(f"Выберите дату", user.chat_id, call.message.message_id, reply_markup=key)

    elif result:
        bot.edit_message_text(f"Введенная дата заезда {result} ", call.message.chat.id, call.message.message_id)

        data_now = time.strftime("%Y-%m-%d")

        if str(result) < str(
                data_now):  # если введенная дата до сегодняшней даты, то вывод ошибки и отправка на перезапрос даты
            bot.send_message(user.chat_id,
                             'Введенная вами дата не корректна (дата заезда не может быть до сегодняшней даты)\nПопробуйте еще раз')
            check_in_data(call.message)
        else:
            user.check_in = result
            logger.debug(f"Пользователь: {user.name_user}, выбрал дату заезда: {user.check_in}")
            check_out_data(call.message)


@bot.callback_query_handler(
    func=DetailedTelegramCalendar.func(calendar_id=2))  # Коллбэк, для обработки нажатия на кнопки выбора даты выезда
def cal1(call):
    """
        Коллбэк, для обработки нажатия на кнопки выбора даты выезда
        А так же записи в класс пользователь даты выезда
        :param call:сообщение от пользователя

    """

    user = Users.get_user(call.message.chat.id, call.message.chat.first_name, call.message.chat.last_name)
    result, key, step = DetailedTelegramCalendar(calendar_id=2, locale='ru').process(call.data)

    if not result and key:
        bot.edit_message_text(f"Выберите дату", user.chat_id, call.message.message_id,
                              reply_markup=key)

    elif result:
        bot.edit_message_text(f"Введенная дата выезда {result} ", call.message.chat.id, call.message.message_id)

        if str(result) < str(
                user.check_in):  # если введенная дата до даты заселения, то вывод ошибки и отправка на перезапрос даты
            bot.send_message(user.chat_id,
                             'Введенная вами дата не корректна (дата выезда не может быть позже даты заезда)\nПопробуйте еще раз')
            check_out_data(call.message)
        else:
            user.check_out = result
            logger.debug(f"Пользователь: {user.name_user}, выбрал дату выезда: {user.check_out}")

            if user.user_command == 'bestdeal':
                logger.debug(f"Пользователь: {user.name_user}, запрос диапазона цен ")

                bot.send_message(user.chat_id,
                                 f"Введите диапазон цен (через - ) {list_emoji['цена']}.\nПример 1000-5000")
                bot.register_next_step_handler(call.message, min_price)
            if user.user_command == 'lowprice' or user.user_command == 'highprice':
                logger.debug(f"Пользователь: {user.name_user}, запрос кол-ва отелей для поиска")

                bot.send_message(user.chat_id, f"Введите количество отелей для поиска {list_emoji['количество']}")
                bot.register_next_step_handler(call.message, request_hotels)


def city_request(message):
    """
    Функция сохранения введенного города и запроса у API районов, введенного города, а так же вывода найденных районов в указанном городе
    :param message:
    """

    user = Users.get_user(message.chat.id, message.from_user.first_name, message.from_user.last_name)
    user.city = message.text  # запись введенного города пользователем

    logger.debug(
        f"Пользователь: {user.name_user}, введен город -  {user.city}")

    if message.text in list_commands:  # если введена команда из списка команд, то бот прекращает все опросы и выводит список доступных команд
        bot.send_message(user.chat_id, 'Ввод остановлен\nВот список доступных команд:\n{}'.format(start_message))
        breakpoint()

    pattern = re.compile(normal)
    checking_city = pattern.search(user.city) is not None  # проверка введенного города на наличие символов, цифр

    try:
        if checking_city == True:

            logger.debug(f"Пользователь: {user.name_user}, Запрос на поиск города -  {user.city}")

            if user.user_command == 'lowprice':  # если пользователь ввел lowprice
                try:
                    user.list_districts = lowprice.get_id_city_lowprice(
                        user.city)  # вызываем функцию запроса районов города в АПИ в файле lowprice.ру, при получении положительного результата сохраняем в класс пользователь\ список районов в введенном городе
                except BaseException as file:
                    logger.debug(
                        f'Ошибка получения списка районов в введенном городе\nЗапрос - lowprice, функция - city_request, ошибки - {file}')
                    bot.send_message(user.chat_id,
                                     f"Произошла ошибка запроса к API {list_emoji['грусть']}\nПожалуйста, попробуйте еще раз")
                    bot.send_message(user.chat_id, start_message)

            elif user.user_command == 'highprice':  # если пользователь ввел highprice
                try:
                    user.list_districts = highprice.get_id_city_highprice(
                        user.city)  # вызываем функцию запроса районов города в АПИ в файле highprice.ру, при получении положительного результата сохраняем в класс пользователь\ список районов в введенном городе
                except BaseException as file:
                    logger.debug(
                        f'Ошибка получения списка районов в введенном городе\nЗапрос - highprice, функция - city_request, ошибки - {file}')
                    bot.send_message(user.chat_id,
                                     f"Произошла ошибка запроса к API {list_emoji['грусть']}\nПожалуйста, попробуйте еще раз")
                    bot.send_message(user.chat_id, start_message)

            elif user.user_command == 'bestdeal':  # если пользователь ввел bestdeal
                try:
                    user.list_districts = bestdeal.get_id_city_bestdeal(
                        user.city)  # вызываем функцию запроса районов города в АПИ в файле bestdeal.ру, при получении положительного результата сохраняем в класс пользователь\ список районов в введенном городе
                except BaseException as file:
                    logger.debug(
                        f'Ошибка получения списка районов в введенном городе\nЗапрос - bestdeal, функция - city_request, ошибки - {file}')
                    bot.send_message(user.chat_id,
                                     f"Произошла ошибка запроса к API {list_emoji['грусть']}\nПожалуйста, попробуйте еще раз")
                    bot.send_message(user.chat_id, start_message)

            if len(user.list_districts) == 0:
                bot.send_message(user.chat_id, f"Хм, введенный вами город не найден {list_emoji['грусть']}")
                bot.send_message(user.chat_id, f"Введите город, в котором будем искать отели {list_emoji['город']}")
                bot.register_next_step_handler(message, city_request)

            else:
                logger.debug(f"Пользователь: {user.name_user}, Запрос на поиск города -  {user.city} УДАЧНО ЗАВЕРШЕН")

                markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                for i in user.list_districts:
                    item1 = types.KeyboardButton(i)
                    markup.add(item1)
                bot.send_message(message.chat.id, 'Выберите район', reply_markup=markup)

                logger.debug(f"Пользователь: {user.name_user}, Запрос на выбор района в веденном городе")

        else:
            bot.send_message(user.chat_id,
                             'Ошибка, в слове присутствуют специальные символы, пробелы или цифры!!!\nПопробуйте еще раз ввести город')
            bot.register_next_step_handler(message, city_request)

    except BaseException as file:
        logger.debug(f'Ошибка запроса к апи, для вывода найденных районов в указанном городе, ошибки - {file}')  #


def check_in_data(message):
    """
    Функция инициализации календаря, для выбора даты заезда
    :param message:
    """

    user = Users.get_user(message.chat.id, message.from_user.first_name, message.from_user.last_name)
    logger.debug(f"Пользователь: {user.name_user}, начало выбора даты заезда ")

    calendar, step = DetailedTelegramCalendar(calendar_id=1, locale='ru').build()
    bot.send_message(user.chat_id, f"Выберите дату заезда ", reply_markup=calendar)


def check_out_data(message):
    """
        Функция инициализации календаря, для выбора даты выезда
        :param message:

    """

    user = Users.get_user(message.chat.id, message.chat.first_name, message.chat.last_name)
    logger.debug(f"Пользователь: {user.name_user}, начало выбора даты выезда ")
    calendar, step = DetailedTelegramCalendar(calendar_id=2, locale='ru').build()
    bot.send_message(user.chat_id, f"Выберите дату выезда ", reply_markup=calendar)


def request_hotels(message):
    """
    Функция сохранения кол-ва отелей для поиска, проверки введенного значения, запроса на выгрузку фотографий (ДА\НЕТ)
    :param message:
    """
    try:
        user = Users.get_user(message.chat.id, message.from_user.first_name, message.from_user.last_name)

        if message.text in list_commands:  # если введена команда из списка команд, то бот прекращает все опросы и выводит список доступных команд
            bot.send_message(user.chat_id, 'Ввод остановлен\nВот список доступных команд:\n{}'.format(start_message))
            breakpoint()

        user.user_count_hotels = message.text

        if user.user_count_hotels.isdigit() == True:  # если введено число

            if int(user.user_count_hotels) > 25:  # сли запрошено более 25 отелей
                bot.send_message(user.chat_id,
                                 'Превышен максимум выводимых отелей за раз\nВам выведется 25 отелей')  # то выводим сообщение о превышении вывода максимального значения
                user.user_count_hotels = 25  # присваиваем переменной кол-во отелей = 25

                logger.debug(
                    f"Пользователь: {user.name_user}, выбрал кол-во отелей = {user.user_count_hotels} ")

                bot.send_message(user.chat_id, f"Нужна ли загрузка фотографий ? {list_emoji['фото']}(Да/Нет)")

                logger.debug(
                    f"Пользователь: {user.name_user}, запрос на вывод фото")

                bot.register_next_step_handler(message, count_photo)

            elif int(user.user_count_hotels) <= 0:
                bot.send_message(user.chat_id,
                                 f"Вы ввели 0 отелей {list_emoji['вопрос']}\nПожалуйста, попробуйте еще раз")  # то выводим сообщение о превышении вывода максимального значения
                bot.send_message(user.chat_id,
                                 'Введите количество отелей для поиска')  # то выводим сообщение о превышении вывода максимального значения
                bot.register_next_step_handler(message, request_hotels)

            else:
                user.user_count_hotels = int(message.text)

                logger.debug(
                    f"Пользователь: {user.name_user}, выбрал кол-во отелей = {user.user_count_hotels} ")

                bot.send_message(user.chat_id, f"Нужна ли загрузка фотографий ? {list_emoji['фото']}(Да/Нет)")

                logger.debug(
                    f"Пользователь: {user.name_user}, запрос на вывод фото")

                bot.register_next_step_handler(message, count_photo)
        else:
            bot.send_message(user.chat_id,
                             f"Ошибка ввода, введено не число {list_emoji['вопрос']}\nПожалуйста, попробуйте еще раз")  # то выводим сообщение о превышении вывода максимального значения
            bot.send_message(user.chat_id,
                             'Введите количество отелей для поиска')  # то выводим сообщение о превышении вывода максимального значения
            bot.register_next_step_handler(message, request_hotels)
    except BaseException as file:
        logger.debug(f'Ошибка сохранения кол-ва отелей, функция - request_hotels, ошибки - {file}')


def count_photo(message):
    """
    Функция:
    - сохранения введенного ответа(ДА\НЕТ)
    - проверки введенного ответа(отсев ответов, кроме ДА\НЕТ)
    - запроса к апи на вывод результатов поиска отелей, по заданным параметрам (если запрос вывода отелей без фото)
    - вывода найденных отелей (если запрос вывода отелей без фото)
    - сохранение найденных отелей в БД
    - Запрос кол-ва фотографий (если ответ на вывод фото == ДА)
    :param message: сообщение от пользователя
    """
    user = Users.get_user(message.chat.id, message.from_user.first_name, message.from_user.last_name)

    if message.text in list_commands:  # если введена команда из списка команд, то бот прекращает все опросы и выводит список доступных команд
        bot.send_message(user.chat_id, 'Ввод остановлен\n{}'.format(start_message))
        breakpoint()

    user.user_answer_photo = message.text.lower()  # записываем введенную строку в переменную

    if user.user_answer_photo == 'да':  # если ответ ДА

        logger.debug(
            f"Пользователь: {user.name_user}, запрос на вывод фото = {user.user_answer_photo}")

        bot.send_message(user.chat_id,
                         f"Укажите количество фотографий {list_emoji['количество']}")  # то запрашиваем кол-во фото

        logger.debug(
            f"Пользователь: {user.name_user}, запрос кол-ва выводимых фото")

        bot.register_next_step_handler(message, number_photo)  # вызываем функцию запроса кол-ва фото

    elif user.user_answer_photo == 'нет':  # если ответ Нет то

        logger.debug(
            f"Пользователь: {user.name_user}, запрос на вывод фото = {user.user_answer_photo}")

        user.user_count_photo = 0  # присваиваем  переменной кол-во фото значение 0
        bot.send_message(user.chat_id, f"Пожалуйста подождите, ваш запрос обрабатывается {list_emoji['обработка']}")

        logger.debug(
            f"Пользователь: {user.name_user}, запрос кол-ва выводимых фото")

        requests_hotel_api(message)

    else:
        bot.send_message(user.chat_id,
                         f"Ошибка ввода {list_emoji['грусть']}")  # выводим сообщение о не корректном вводе
        bot.send_message(user.chat_id, 'Нужна ли загрузка фотографий ? (Да/Нет)')  # запрашиваем еще раз
        bot.register_next_step_handler(message, count_photo)  # вызываем функцию еще раз


def number_photo(message):
    """
    Функция:
    - сохранения кол-ва фото
    - проверки введенного кол-ва фото
    - проверки введенных результатов (если введен текст, а не сообщение, то повторный запрос, с выводом ошибки)
    - формирование и запрос к апи
    - формирование медиа группы для вывода результата + альбома фото
    - сохранение найденных отелей в БД
    :param message: сообщение от пользователя
    """

    user = Users.get_user(message.chat.id, message.from_user.first_name, message.from_user.last_name)

    if message.text in list_commands:  # если введена команда из списка команд, то бот прекращает все опросы и выводит список доступных команд
        bot.send_message(user.chat_id, 'Ввод остановлен\nВот список доступных команд:\n{}'.format(start_message))
        breakpoint()

    user.user_count_photo = message.text

    if user.user_count_photo.isdigit() == True:  # если введено число

        if int(user.user_count_photo) == 0:  # если введено 0 фотографий
            bot.send_message(user.chat_id,
                             f"Количество выводимых фотографий не может быть = 0 {list_emoji['грусть']}\nПожалуйста, попробуйте еще раз")  # то выводим сообщение о ошибке
            bot.send_message(user.chat_id, 'Укажите количество фотографий.')  # запрашиваем результат повторно
            bot.register_next_step_handler(message, number_photo)  # вызываем фнкцию еще раз

        if int(user.user_count_photo) > 10:  # если введено больше 10 фотографий
            user.user_count_photo = 10

            logger.debug(
                f"Пользователь: {user.name_user}, запрос кол-ва выводимых фото = {user.user_count_photo}")

            bot.send_message(user.chat_id,
                             f"Количество выводимых фотографий не может быть больше 10 {list_emoji['грусть']}\nВам выведется 10 фотографий")  # выводим сообщение о превышении допустимого максимума вывода фотографий
            bot.send_message(user.chat_id, f"Пожалуйста подождите, ваш запрос обрабатывается {list_emoji['обработка']}")
            requests_hotel_api(message)

        else:
            user.user_count_photo = int(message.text)

            logger.debug(
                f"Пользователь: {user.name_user}, запрос кол-ва выводимых фото = {user.user_count_photo}")

            bot.send_message(user.chat_id, f"Пожалуйста подождите, ваш запрос обрабатывается {list_emoji['обработка']}")
            requests_hotel_api(message)


    else:
        bot.send_message(user.chat_id,
                         f"Ошибка ввода, введено не число {list_emoji['вопрос']}\nПожалуйста, попробуйте еще раз")  # то выводим сообщение о превышении вывода максимального значения
        bot.send_message(user.chat_id,
                         'Укажите количество фотографий.')  # то выводим сообщение о превышении вывода максимального значения
        bot.register_next_step_handler(message, number_photo)


def answer_max_distance(message):  # метод запроса диапазона расстояния от центра
    """
    Функция:
    - сохранения минимальной дистанции
    - проверки введенного расстояния на число( введено число или текст)
    :param message: сообщение от пользователя
    """
    try:
        user = Users.get_user(message.chat.id, message.from_user.first_name, message.from_user.last_name)

        if message.text in list_commands:  # если введена команда из списка команд, то бот прекращает все опросы и выводит список доступных команд
            bot.send_message(user.chat_id, 'Ввод остановлен\nВот список доступных команд:\n{}'.format(start_message))
            breakpoint()

        if message.text.isdigit() == True:  # если введено число
            if int(message.text) == 0:  # если введенное число равно 0
                bot.send_message(user.chat_id,
                                 f"Расстояние не может быть = 0 {list_emoji['вопрос']},\nПожалуйста, попробуйте еще раз")  # выводим ошибку ввода
                bot.send_message(user.chat_id, 'Введите максимальное расстояние от центра в километрах')
                bot.register_next_step_handler(message, answer_max_distance)  # запрашиваем повторно
            else:  # иначе
                user.max_distance = int(message.text)  # присваиваем переменной введенное значение

                logger.debug(
                    f"Пользователь: {user.name_user}, выбрал максимальное расстояние от центра = {user.max_distance} км ")

                bot.send_message(user.chat_id,
                                 f"Введите количество отелей для поиска {list_emoji['количество']}")  # выводим следующий вопрос

                logger.debug(
                    f"Пользователь: {user.name_user}, запрос кол-ва отелей для поиска ")

                bot.register_next_step_handler(message, request_hotels)  # вызываем следующую функцию
        else:  # если введено было не число
            bot.send_message(user.chat_id,
                             f"Ошибка ввода {list_emoji['количество']}\nВы ввели не число, пожалуйста попробуйте еще раз ")  # выводим ошибку ввода
            bot.send_message(user.chat_id, 'Введите максимальное расстояние от центра в километрах')
            bot.register_next_step_handler(message, answer_max_distance)  # запрашиваем повторно
    except BaseException as file:
        logger.debug(f'Ошибка записи максимальное дистанции, функция - answer_min_distance, ошибки - {file}')


def min_price(message):
    """
    Функция:
    - обработки и записи минимальной и максимальной цены за введенную дату проживания
    - проверка, введено ли число или текст
    - вызова и запроса минимальной дистанции
    :param message: сообщение от пользователя
    """
    try:
        user = Users.get_user(message.chat.id, message.from_user.first_name, message.from_user.last_name)

        if message.text in list_commands:  # если введена команда из списка команд, то бот прекращает все опросы и выводит список доступных команд
            bot.send_message(user.chat_id, 'Ввод остановлен\nВот список доступных команд:\n{}'.format(start_message))
            breakpoint()

        if message.text.split('-')[0].isdigit() and message.text.split('-')[
            1].isdigit() == True:  # проверка, были ли введены числа

            if int(message.text.split('-')[0]) == 0:  # если введенное число равно 0
                bot.send_message(user.chat_id,
                                 f"Минимальна цена за проживание не может быть = 0 {list_emoji['вопрос']}\nПожалуйста, попробуйте еще раз")  # то выводим сообщение о ошибки
                bot.send_message(user.chat_id,
                                 f"Введите диапазон цен ( через - ) {list_emoji['цена']}\nПример 1000-5000")
                bot.register_next_step_handler(message, min_price)  # вызываем функцию еще раз
            else:  # иначе
                user.user_min_price = int(
                    message.text.split('-')[0])  # присваиваем переменной введенное значение (минимальная цена)
                user.user_max_price = int(
                    message.text.split('-')[1])  # присваиваем переменной введенное значение (максимальная цена)

                logger.debug(
                    f"Пользователь: {user.name_user}, выбрал минимальную цену - {user.user_min_price}, максимальную цену -  {user.user_max_price} ")

                bot.send_message(user.chat_id,
                                 f" Введите максимальное расстояние от центра в километрах {list_emoji['расстояние']}")  # выводим следующий вопрос

                logger.debug(
                    f"Пользователь: {user.name_user}, запрос максимального расстояния от центра ")

                bot.register_next_step_handler(message, answer_max_distance)  # вызываем следующую функцию

        else:  # если введено было не число
            bot.send_message(user.chat_id,
                             f"Ошибка ввода {list_emoji['вопрос']}\nОдин из введенных параметров цены не число, пожалуйста попробуйте еще раз")  # выводим ошибку ввода
            bot.send_message(user.chat_id, 'Введите диапазон цен ( через - ).\nПример 1000-5000')
            bot.register_next_step_handler(message, min_price)  # запрашиваем повторно
    except BaseException as file:
        logger.debug(f'Ошибка получения и записи диапазона цен, функция - min_price, ошибки - {file}')


def requests_hotel_api(message):
    """
    Функция:
    - запроса к апи, для поиска отелей в выбранном районе города
    - вывод фотографий отеля ( при необходимости)
    - сохранения найденных отелей БД
    :param message: Сообщение от пользователя
    :return:
    """
    user = Users.get_user(message.chat.id, message.from_user.first_name, message.from_user.last_name)
    list_hotel = ''
    if user.user_command == 'lowprice':
        try:
            logger.debug(
                f"Пользователь: {user.name_user}, запрос к API, для поиска отелей в выбранном районе,  команда - {user.user_command}")
            list_hotel = lowprice.get_hotels_lowprice(user.id_city, user.user_count_hotels, user.check_in,
                                                      user.check_out).items()
        except BaseException as file:
            logger.debug(f'Ошибка поиска отелей, функция - requests_hotel_api , запрос - lowprice, ошибки - {file}')

        if len(list_hotel) == 0:
            bot.send_message(user.chat_id,
                             f"В введенном вами районе нет отелей, либо вы ввели район не корректно\nПопробуйте еще раз\n{start_message}")
        else:
            logger.debug(
                f"Пользователь: {user.name_user}, запрос к API, для поиска отелей УДАЧНО ЗАВЕРШЕН,  команда - {user.user_command}")
            bot.send_message(user.chat_id, 'Найденные отели по вашему запросу ')  # вывод сообщения пользователю
            user.history_hotels = ''  # обнуляем записанные отели

            for hotel_id, hotel_info in list_hotel:  # идем циклом по словарю с найденными отелями и фотографиями
                user.history_hotels += f"{''.join(hotel_info)}\n\n"  # записываем отели для записи в базу данных  в переменную истории найденных отелей
                bot.send_message(user.chat_id, hotel_info)  # отправляем данные отеля пользователю
                if user.user_answer_photo == 'да':  # если вывод с фото, то вызываем функцию запроса фото у каждого отеля
                    try:
                        logger.debug(
                            f"Пользователь: {user.name_user}, запрос к API, для вывода фото к отелю - {user.user_command}")
                        media = lowprice.get_hotel_photo(hotel_id, user.user_count_photo)
                        bot.send_media_group(user.chat_id, media=media)
                        logger.debug(
                            f"Пользователь: {user.name_user}, запрос к API, для вывода фото УДАЧНО ЗАВЕРШЕН, команда - {user.user_command}")
                    except BaseException as file:
                        logger.debug(
                            f'Ошибка получения фотографий у каждого из отелей\nРаздел lowprice, функция - requests_hotel_api, ошибки - {file}')
                        bot.send_message(user.chat_id,
                                         f"К сожалению не удалось получить фотографии отеля\n {list_emoji['грусть']}\nПопробуйте еще раз\n{start_message}")

            try:
                history.seve(user.name_user, user.id_line, user.chat_id, user.user_command, user.time, user.city,
                             user.user_count_hotels, user.user_answer_photo, user.user_count_photo,
                             user.user_min_price, user.user_max_price, user.max_distance, user.history_hotels)
            except BaseException as file:
                logger.debug(f'Ошибка сохранения истории поиска, ошибки - {file}')

    if user.user_command == 'highprice':
        try:
            logger.debug(
                f"Пользователь: {user.name_user}, запрос к API, для поиска отелей в выбранном районе,  команда - {user.user_command}")
            list_hotel = highprice.get_hotels_highprice(user.id_city, user.user_count_hotels, user.check_in,
                                                        user.check_out).items()
        except BaseException as file:
            logger.debug(f'Ошибка поиска отелей, функция - requests_hotel_api , запрос - highprice, ошибки - {file}')

        if len(list_hotel) == 0:
            bot.send_message(user.chat_id,
                             f"В введенном вами районе нет отелей, либо вы ввели район не корректно\nПопробуйте еще раз\n{start_message}")
        else:
            logger.debug(
                f"Пользователь: {user.name_user}, запрос к API, для поиска отелей УДАЧНО ЗАВЕРШЕН,  команда - {user.user_command}")
            bot.send_message(user.chat_id, 'Найденные отели по вашему запросу')  # вывод сообщения пользователю
            user.history_hotels = ''  # обнуляем записанные отели

            for hotel_id, hotel_info in list_hotel:  # идем циклом по словарю с найденными отелями и фотографиями
                user.history_hotels += f"{''.join(hotel_info)}\n\n"  # записываем отели для записи в базу данных  в переменную истории найденных отелей
                bot.send_message(user.chat_id, hotel_info)
                if user.user_answer_photo == 'да':
                    try:
                        logger.debug(
                            f"Пользователь: {user.name_user}, запрос к API, для вывода фото к отелю - {user.user_command}")
                        media = lowprice.get_hotel_photo(hotel_id, user.user_count_photo)
                        bot.send_media_group(user.chat_id, media=media)
                        logger.debug(
                            f"Пользователь: {user.name_user}, запрос к API, для вывода фото УДАЧНО ЗАВЕРШЕН, команда - {user.user_command}")
                    except BaseException as file:
                        logger.debug(
                            f'Ошибка получения фотографий у каждого из отелей\nРаздел highprice, функция - requests_hotel_api, ошибки - {file}')
                        bot.send_message(user.chat_id,
                                         f"К сожалению не удалось получить фотографии отеля\n {list_emoji['грусть']}\nПопробуйте еще раз\n{start_message}")

            try:
                history.seve(user.name_user, user.id_line, user.chat_id, user.user_command, user.time, user.city,
                             user.user_count_hotels, user.user_answer_photo, user.user_count_photo,
                             user.user_min_price, user.user_max_price, user.max_distance, user.history_hotels)
            except BaseException as file:
                logger.debug(f'Ошибка сохранения истории поиска, ошибки - {file}')

    if user.user_command == 'bestdeal':
        try:
            logger.debug(
                f"Пользователь: {user.name_user}, запрос к API, для поиска отелей в выбранном районе,  команда - {user.user_command}")
            list_hotel = bestdeal.get_hotels_bestdeal(user.id_city, user.user_count_hotels, user.user_min_price,
                                                      user.user_max_price, user.max_distance, user.check_in,
                                                      user.check_out,
                                                      user.coordinates).items()
        except BaseException as file:
            logger.debug(f'Ошибка поиска отелей, функция - requests_hotel_api , запрос - bestdeal, ошибки - {file}')

        if len(list_hotel) == 0:
            bot.send_message(user.chat_id,
                             f"В введенном вами районе нет отелей, либо вы ввели район не корректно\nПопробуйте еще раз\n{start_message}")
        else:
            logger.debug(
                f"Пользователь: {user.name_user}, запрос к API, для поиска отелей УДАЧНО ЗАВЕРШЕН,  команда - {user.user_command}")
            bot.send_message(user.chat_id, 'Найденные отели по вашему запросу')  # вывод сообщения пользователю
            user.history_hotels = ''  # обнуляем записанные отели

            for hotel_id, hotel_info in list_hotel:  # идем циклом по словарю с найденными отелями и фотографиями
                user.history_hotels += f"{''.join(hotel_info)}\n\n"  # записываем отели для записи в базу данных  в переменную истории найденных отелей
                bot.send_message(user.chat_id, hotel_info)
                if user.user_answer_photo == 'да':
                    try:
                        logger.debug(
                            f"Пользователь: {user.name_user}, запрос к API, для вывода фото к отелю - {user.user_command}")
                        media = lowprice.get_hotel_photo(hotel_id, user.user_count_photo)
                        bot.send_media_group(user.chat_id, media=media)
                        logger.debug(
                            f"Пользователь: {user.name_user}, запрос к API, для вывода фото УДАЧНО ЗАВЕРШЕН, команда - {user.user_command}")
                    except BaseException as file:
                        logger.debug(
                            f'Ошибка получения фотографий у каждого из отелей\nРаздел bestdeal, функция - requests_hotel_api, ошибки - {file}')
                        bot.send_message(user.chat_id,
                                         f"К сожалению не удалось получить фотографии отеля\n {list_emoji['грусть']}\nПопробуйте еще раз\n{start_message}")

            try:
                history.seve(user.name_user, user.id_line, user.chat_id, user.user_command, user.time, user.city,
                             user.user_count_hotels, user.user_answer_photo, user.user_count_photo,
                             user.user_min_price, user.user_max_price, user.max_distance, user.history_hotels)
            except BaseException as file:
                logger.debug(f'Ошибка сохранения истории поиска, ошибки - {file}')


def get_history(message):
    """
    Функция:
    - вывода истории поиска
    - проверка введенных параметров
    :param message: сообщение от пользователя
    """

    user = Users.get_user(message.chat.id, message.from_user.first_name, message.from_user.last_name)

    if message.text in list_commands:  # если введена команда из списка команд, то бот прекращает все опросы и выводит список доступных команд
        bot.send_message(user.chat_id, 'Ввод остановлен\nВот список доступных команд:\n{}'.format(start_message))
        breakpoint()

    if message.text.isdigit() == True:

        if int(message.text) == 1:
            try:
                logger.debug(
                    f"Пользователь: {user.name_user}, выбрал режим вывода всей истории поиска")

                bot.send_message(user.chat_id, f"Начинается выгрузка истории поиска {list_emoji['поиск']}")
                database = 'history.db'
                with sqlite3.connect(database) as connection:
                    connection.row_factory = sqlite3.Row
                    cursor = connection.cursor()
                    sqlite_select_query = f"""SELECT * FROM {user.name_user} """
                    cursor.execute(sqlite_select_query)
                    records = cursor.fetchall()

                    for i in records:
                        bot.send_message(user.chat_id,
                                         f'Команда - {i[2]}\n\nВремя ввода команды - {i[3]}\n\nОтели: \n{i[11]}')
                logger.debug(
                    f"Пользователь: {user.name_user}, История поиска выведена")
            except BaseException as mistake:
                error_variant = str(mistake)
                if 'no such table' in error_variant:
                    bot.send_message(user.chat_id,
                                     f"Ошибка {list_emoji['грусть']}\nВы пытаетесь запросить историю поиска, не общаясь с ботом ранее\nДля зпроса истории поиска необходимо пообщатьсяс ботом\n{start_message}")
                else:
                    bot.send_message(user.chat_id,
                                     f"Ошибка {list_emoji['грусть']}\nчто-то пошло не так, пожалуйста попробуйте еще раз")
                    bot.send_message(user.chat_id,
                                     'Введите 1 - для вывода всей истории поиска\nВведите 2 - для вывода последнего запроса')  # запрашиваем кол-во отелей
                    bot.register_next_step_handler(message, get_history)
                    logger.debug(
                        f'Ошибка вывода истории поиска в режиме вывода всей истории поиска, фунция - get_history, ошибки - {mistake}')



        elif int(message.text) == 2:
            try:
                logger.debug(
                    f"Пользователь: {user.name_user}, выбрал режим вывода последнего поиска")
                bot.send_message(user.chat_id, f"Начинается выгрузка истории поиска {list_emoji['поиск']}")
                database = 'history.db'
                with sqlite3.connect(database) as connection:
                    connection.row_factory = sqlite3.Row
                    cursor = connection.cursor()
                    sqlite_select_query = f"""SELECT * FROM {user.name_user} """
                    cursor.execute(sqlite_select_query)
                    records = cursor.fetchall()
                    t = records[-1]
                    bot.send_message(user.chat_id,
                                     f'Команда - {t[2]}\n\nВремя ввода команды - {t[3]}\n\nОтели: \n{t[11]}')
                logger.debug(
                    f"Пользователь: {user.name_user}, История поиска выведена")
            except BaseException as mistake:
                error_variant = str(mistake)
                if 'no such table' in error_variant:
                    bot.send_message(user.chat_id,
                                     f"Ошибка {list_emoji['грусть']}\nВы пытаетесь запросить историю поиска, не общаясь с ботом ранее\nДля зпроса истории поиска необходимо пообщатьсяс ботом\n{start_message}")
                else:
                    bot.send_message(user.chat_id,
                                     f"Ошибка {list_emoji['грусть']}\nчто-то пошло не так, пожалуйста попробуйте еще раз")
                    bot.send_message(user.chat_id,
                                     'Введите 1 - для вывода всей истории поиска\nВведите 2 - для вывода последнего запроса')  # запрашиваем кол-во отелей
                    bot.register_next_step_handler(message, get_history)
                    logger.debug(
                        f'Ошибка вывода истории поиска в режиме вывода всей истории поиска, фунция - get_history, ошибки - {mistake}')



        else:
            bot.send_message(user.chat_id, f"Не корректный ввод {list_emoji['грусть']}\nПопробуйте еще раз")
            bot.send_message(user.chat_id,
                             'Введите 1 - для вывода всей истории поиска\nВведите 2 - для вывода последнего запроса')  # запрашиваем кол-во отелей
            bot.register_next_step_handler(message, get_history)
            logger.debug('Ошибка ввода, пользователь вводит не заданный режим вывода истории, фунция - get_history')

    else:
        bot.send_message(user.chat_id, f"Не корректный ввод {list_emoji['грусть']}\nПопробуйте еще раз")
        bot.send_message(user.chat_id,
                         'Введите 1 - для вывода всей истории поиска\nВведите 2 - для вывода последнего запроса')  # запрашиваем кол-во отелей
        bot.register_next_step_handler(message, get_history)


if __name__ == '__main__':
    bot.polling()
