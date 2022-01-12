class Users:
    """
    Класс пользователь:
    - выполняет функцию хранения всех необходимых данных, для запросов к АПИ
    """
    user = {}

    def __init__(self, chat_id, first_name, last_name):
        self.chat_id = chat_id  # чат айди, для общения с пользователем
        self.last_name = last_name  # фамилия пользователя
        self.city = None  # запрос города у пользователя
        self.id_city = None  #
        self.name_user = first_name  # ник пользователя
        self.user_id = None  # айди пользователя
        self.user_command = None  # команды пользователя
        self.time = None  # время ввода команды
        self.user_count_hotels = None  # кол-во отелей
        self.user_min_price = None  # минимальная стоимость
        self.user_max_price = None  # максимальная стоимость
        self.max_distance = None  # максимальная дистанция отеля от центра
        self.user_answer_photo = None  # запрос о показе фото ( Да\Нет)
        self.user_count_photo = None  # кол-во фото
        self.check_in = None  # дата заселения
        self.check_out = None  # дата выселения
        self.id_line = 0  # переменная, необходимая для определения айди строки в БД
        self.history_hotels = ''  # история найденных отелей, для записи в БД
        self.list_districts = None  # список найденных районов в веденном городе
        self.coordinates = None  # координаты выбранного района

    @classmethod
    def get_user(cls, chat_id, name, surname):
        if chat_id in cls.user.keys():
            return cls.user[chat_id]
        else:
            return cls.add_user(chat_id, name, surname)

    @classmethod
    def add_user(cls, chat_id, name, surname):
        cls.user[chat_id] = Users(chat_id, name, surname)
        return cls.user[chat_id]
