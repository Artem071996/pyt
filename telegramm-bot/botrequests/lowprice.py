# Команда /lowprice — вывод самых дешёвых отелей в городе
# После ввода команды у пользователя запрашивается:
# 1. Город, где будет проводиться поиск.
# 2. Количество отелей, которые необходимо вывести в результате (не больше
# заранее определённого максимума).
# 3. Необходимость загрузки и вывода фотографий для каждого отеля (“Да/Нет”)
# a. При положительном ответе пользователь также вводит количество
# необходимых фотографий (не больше заранее определённого
# максимума)

import requests  # библиотека для парсинга
import json  # библиотека для работы с json файлами
import os

from dotenv import load_dotenv  # библиотека для получения АЙПИ адресов
from loguru import logger  # библиотека для логирования ошибок

from telebot.types import InputMediaPhoto  # библиотека формирования медиа группы, для отправки альбомов с фото

load_dotenv()

headers = {'x-rapidapi-host': "hotels4.p.rapidapi.com", 'x-rapidapi-key': os.getenv('KEY_RAPIDAPI')}


def get_id_city_lowprice(city):  # функция получения айди введенного города
    """
    Функция запроса к API, для получения списка районов в веденном городе
    :param city: введенный пользователем город
    :return id_city: словарь найденных районов в веденном городе, где ключ - название района, значение - данные по району
    """

    id_city = dict()  # хранение айди города

    url = "https://hotels4.p.rapidapi.com/locations/v2/search"

    querystring = {"query": city, "locale": "ru_RU"}

    response = requests.request("GET", url, headers=headers, params=querystring)
    data_site_citi = response.text  # полученные данные с сайта
    converted_data = json.loads(data_site_citi)  # конвертированные данные для удобной работы
    for i in converted_data['suggestions'][0]['entities']:  # идем по значениям словаря
        id_city[i['name']] = i['destinationId'], i['latitude'], i['longitude']

    return id_city  # возвращаем полученные результат


def get_hotels_lowprice(id_city, num_hotels, check_in,
                        check_out):  # функция получения отелей в городе, по полученному айди
    """
    Функция запроса к API, для получения списка отелей в заданном районе
    :param id_city: айди района в выбранном городе
    :param num_hotels: количество отелей в выбранном районе
    :param check_in: дата заезда
    :param check_out: дата выезда
    :return hotels_list: словарь найденных отелей в выбранном районе, где ключ - айди отеля, значение - данные по отелю
    """

    hotels_list = dict()  # словарь найденных отелей в выбранном районе, где ключ - айди отеля, значение - данные по отелю

    url = "https://hotels4.p.rapidapi.com/properties/list"

    querystring = {"destinationId": id_city, "pageNumber": "1", "pageSize": num_hotels,
                   "checkIn": check_in, "checkOut": check_out, "adults1": "1", "sortOrder": "PRICE",
                   "locale": "ru_RU", "currency": "RUB"}
    response = requests.request("GET", url, headers=headers, params=querystring)
    converted_data = json.loads(response.text)  # конвертированные данные для удобной работы
    data_hotel = converted_data['data']['body']['searchResults']['results']  # общие данные отелей

    ch_in = str(check_in)
    ch_out = str(check_out)

    for hotel in data_hotel:
        hotel_id = hotel.get('id')
        hotel_name = hotel.get('name')
        city = hotel.get('address').get('locality')
        if hotel.get('address').get('streetAddress'):
            address = hotel.get('address').get('streetAddress')
        else:
            address = 'К сожалению данный отель не предоставил адреса'
        if hotel['ratePlan']['price']['exactCurrent']:
            price_in_night = int(hotel['ratePlan']['price']['exactCurrent']) // (
                    int(ch_out.split('-')[-1]) - int(ch_in.split('-')[-1]))
        else:
            price_in_night = 'не удалось получить цену'
        price = hotel.get('ratePlan').get('price').get('current')
        info = hotel.get('ratePlan').get('price').get('info')
        hotels_list[hotel_id] = [
            '{name},\nАдрес: {city}, {address}\nСтоимость за ночь: {price_in_night} RUB\nСтоимость: {price}, {info}'.format(
                name=hotel_name, city=city, address=address, price_in_night=price_in_night, price=price, info=info)]

    return hotels_list


def get_hotel_photo(id, count_photo):  # функция получения фотографий по списку отелей
    """
    Функция запроса к API, для получения списка фотографий отеля
    :param id: ади отеля
    :param count_photo: количество фотографий
    :return media_group: список url адресов фотографий отеля
    """

    photos_url_list = list()  # список юрл адресов фотографий отеля
    media_group = list()  # список медиа группы фото отеля, для отправки альбома фото пользователю

    url = "https://hotels4.p.rapidapi.com/properties/get-hotel-photos"
    querystring = {"id": id}
    response = requests.request("GET", url, headers=headers, params=querystring)
    data = json.loads(response.text)  # конвертируем полученные данные с сайта, для нормальной работы

    for i_number, i_photo_info in enumerate(data.get('hotelImages')):
        if i_number == int(count_photo):
            break
        photo_url = i_photo_info.get('baseUrl').format(size='z')
        photos_url_list.append(photo_url)

    for i_url in photos_url_list:
        media_group.append(InputMediaPhoto(media=i_url))

    return media_group
