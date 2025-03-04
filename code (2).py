
import telebot
from telebot import types
import datetime
import time
import os
from threading import Thread
from random import randint

# --- Настройки ---
BOT_TOKEN = "YOUR_BOT_TOKEN"  # Замените на токен вашего бота
ADMIN_PASSWORD = "ADMIN_PASSWORD"  # Замените на пароль администратора
REGISTER_PASSWORD = "REGISTER_PASSWORD"  # Замените на пароль для регистрации
TASKS_FILE_PATH = "Olympiada/olympiad.pdf"  # Путь к файлу с заданиями
OLYMPIAD_START = datetime.datetime(2025, 3, 4, 8, 0, 0)
OLYMPIAD_END = datetime.datetime(2025, 3, 8, 8, 0, 0)
SOLUTION_TIME_LIMIT_SECONDS = 60 * 60  # 1 час в секундах
SOLUTION_FOLDER = "solutions"  # Папка для сохранения решений
USER_DATA_FILE = "user_data.txt"  # Файл для хранения данных пользователей (код, регистрация)
ADMIN_IDS_FILE = "admin_ids.txt"  # Файл для хранения ID администраторов
# --- Инициализация бота ---
bot = telebot.TeleBot(BOT_TOKEN)

# --- Данные в памяти ---
registered_users = {}  # {user_id: {"code": str, "registered": bool, "solution_sent": bool, "solution_time": datetime, "timer_active": bool}}
admin_ids = set()  # Множество ID админов


# --- Функция загрузки данных пользователей из файла ---
def load_user_data():
    global registered_users
    try:
        with open(USER_DATA_FILE, "r") as f:
            for line in f:
                user_id, code, registered, solution_sent, solution_time, timer_active = line.strip().split(",")
                registered_users[int(user_id)] = {
                    "code": code,
                    "registered": registered == "True",
                    "solution_sent": solution_sent == "True",
                    "solution_time": datetime.datetime.fromisoformat(solution_time) if solution_time != "None" else None,
                    "timer_active": timer_active == "True",  # Добавлен новый флаг
                }
    except FileNotFoundError:
        print("Файл user_data.txt не найден. Создается новый.")
    except Exception as e:
        print(f"Ошибка при загрузке данных пользователей: {e}")
        registered_users = {}


# --- Функция сохранения данных пользователей в файл ---
def save_user_data():
    try:
        with open(USER_DATA_FILE, "w") as f:
            for user_id, data in registered_users.items():
                f.write(
                    f"{user_id},{data['code']},{data['registered']},{data['solution_sent']},{data['solution_time']},{data['timer_active']}\n")  # Обновлен формат записи
    except Exception as e:
        print(f"Ошибка при сохранении данных пользователей: {e}")


# --- Функция загрузки ID администраторов ---
def load_admin_ids():
    global admin_ids
    try:
        with open(ADMIN_IDS_FILE, "r") as f:
            for line in f:
                admin_ids.add(int(line.strip()))
    except FileNotFoundError:
        print("Файл admin_ids.txt не найден. Создается новый.")
    except Exception as e:
        print(f"Ошибка при загрузке ID администраторов: {e}")
        admin_ids = set()


# --- Функция сохранения ID администраторов ---
def save_admin_ids():
    try:
        with open(ADMIN_IDS_FILE, "w") as f:
            for admin_id in admin_ids:
                f.write(f"{admin_id}\n")
    except Exception as e:
        print(f"Ошибка при сохранении ID администраторов: {e}")


# --- Загрузка данных при старте бота ---
load_user_data()
load_admin_ids()


# --- Функция генерации уникального 5-значного кода ---
def generate_unique_code():
    code = str(randint(10000, 99999))
    while any(user.get("code") == code for user in registered_users.values()):  # Проверка на уникальность
        code = str(randint(10000, 99999))
    return code


# --- Функция для форматирования времени до конца олимпиады ---
def format_timedelta(delta):
    days = delta.days
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{days} дней, {hours} часов, {minutes} минут, {seconds} секунд"


# --- Обработчики команд ---
def check_timer(message):
    user_id = message.from_user.id
    if user_id in registered_users and registered_users[user_id]["timer_active"]:
        bot.reply_to(message, "Во время решения олимпиады вам доступна только команда /help.")
        return True
    return False


@bot.message_handler(commands=['start'])
def start(message):
    if check_timer(message):
        return
    user_id = message.from_user.id
    username = message.from_user.username
    bot.reply_to(message,
                 f"Привет, {username}. Рад видеть тебя на этой олимпиаде. Чтобы участвовать в олимпиаде, нажмите /register для регистрации.")


@bot.message_handler(commands=['help'])
def help(message):
    bot.reply_to(message, "Краткое описание олимпиады и правила ее проведения. (Здесь должно быть описание)")


@bot.message_handler(commands=['register'])
def register(message):
    if check_timer(message):
        return

    user_id = message.from_user.id
    if user_id in registered_users and registered_users[user_id]["registered"]:
        bot.reply_to(message, "Вы уже зарегистрированы в олимпиаде.")
        return

    msg = bot.reply_to(message, "Введите пароль, который дал организатор:")
    bot.register_next_step_handler(msg, process_register_password)


def process_register_password(message):
    user_id = message.from_user.id
    password = message.text
    if password == REGISTER_PASSWORD:
        code = generate_unique_code()
        registered_users[user_id] = {"code": code, "registered": True, "solution_sent": False,
                                     "solution_time": None, "timer_active": False}
        save_user_data()
        bot.reply_to(message,
                     f"Вы успешно зарегистрировались в этой олимпиаде. Ваш уникальный код: {code}. Чтобы узнать о статусе периода олимпиады нажмите /stat. Для подробной информации и поддержки используйте /help.")  # Добавлено /help
    else:
        bot.reply_to(message, "Пароль неверный. Проверьте пароль и попробуйте еще раз.")
        # Повторный запрос пароля
        msg = bot.reply_to(message, "Введите пароль, который дал организатор:")
        bot.register_next_step_handler(msg, process_register_password)


@bot.message_handler(commands=['stat'])
def stat(message):
    if check_timer(message):
        return
    now = datetime.datetime.now()
    if now < OLYMPIAD_START:
        time_left = OLYMPIAD_START - now
        bot.reply_to(message,
                     "Еще не началась период олимпиады. До начала олимпиады осталось: " + format_timedelta(
                         time_left) + ". Чтобы узнать о подробностях обратитесь к поддержку /help")
    elif OLYMPIAD_START <= now <= OLYMPIAD_END:
        time_left = OLYMPIAD_END - now
        bot.reply_to(message,
                     "Период олимпиады уже начался. До конца периода олимпиады осталось: " + format_timedelta(
                         time_left) + ". Чтобы получит задачи, нажмите /get_tasks. У вас будет ровно 1 час чтобы отправит решение (в формате pdf; ОБЪЯЗАТЕЛЬНО).")
    else:
        bot.reply_to(message, "Период олимпиады уже закончилась. Чтобы узнать о подробностях обратитесь к поддержку /help")


@bot.message_handler(commands=['registered_users'])
def registered_users_list(message):
    user_id = message.from_user.id
    if user_id not in admin_ids:
        bot.reply_to(message, "У вас нет прав для просмотра этой информации.")
        return

    msg = bot.reply_to(message, "Введите 6-значный код администратора:")
    bot.register_next_step_handler(msg, process_admin_password)


def process_admin_password(message):
    user_id = message.from_user.id
    password = message.text
    if password == ADMIN_PASSWORD or user_id in admin_ids:  # Исправлено:  Проверка на ID админа
        user_list = ""
        for user_id, data in registered_users.items():
            try:
                user_obj = bot.get_chat(user_id)
                username = user_obj.username if user_obj.username else "Не указан"
                user_list += f"ID: {user_id}, Код: {data['code']}, Username: @{username}\n"
            except telebot.apihelper.ApiException as e:
                user_list += f"ID: {user_id}, Код: {data['code']}, Username: (Невозможно получить - пользователь заблокировал бота)\n"
        bot.reply_to(message, f"Список зарегистрированных пользователей:\n{user_list}")
    else:
        bot.reply_to(message, "Код администратора неверный.")


@bot.message_handler(commands=['get_tasks'])
def get_tasks(message):
    if check_timer(message):
        return

    user_id = message.from_user.id
    if user_id not in registered_users or not registered_users[user_id]["registered"]:
        bot.reply_to(message, "Вы не зарегистрированы в олимпиаде. Пожалуйста, зарегистрируйтесь с помощью команды /register.")
        return

    msg = bot.reply_to(message, "Введите ваш индивидуальный код:")
    bot.register_next_step_handler(msg, process_task_code)


def process_task_code(message):
    user_id = message.from_user.id
    code = message.text
    if code == registered_users[user_id]["code"]:
        try:
            with open(TASKS_FILE_PATH, 'rb') as file:
                bot.send_document(user_id, file)
            bot.reply_to(message, "Задания отправлены. У вас есть 1 час на решение.")

            registered_users[user_id]["solution_time"] = datetime.datetime.now()
            registered_users[user_id]["solution_sent"] = False
            registered_users[user_id]["timer_active"] = True  # Устанавливаем флаг активности таймера
            save_user_data()

            start_time = datetime.datetime.now()
            end_time = start_time + datetime.timedelta(seconds=SOLUTION_TIME_LIMIT_SECONDS)

            # Запуск таймера в отдельном потоке
            Thread(target=solution_timer, args=(user_id, end_time)).start()


        except FileNotFoundError:
            bot.reply_to(message, "Файл с заданиями не найден.")
        except Exception as e:
            bot.reply_to(message, f"Произошла ошибка при отправке файла: {e}")
    else:
        bot.reply_to(message, "Вы ввели неверный код. Попробуйте снова или обратитесь в поддержку /help.")


def solution_timer(user_id, end_time):
    while datetime.datetime.now() < end_time:
        remaining_time = end_time - datetime.datetime.now()
        hours, remainder = divmod(remaining_time.total_seconds(), 3600)
        minutes, seconds = divmod(remainder, 60)

        # Уменьшаем интервалы отправки сообщений по мере приближения к концу таймера
        if remaining_time.total_seconds() > 600:  # Больше 10 минут
            sleep_time = 600  # 10 минут
        elif remaining_time.total_seconds() > 60:  # Больше 1 минуты
            sleep_time = 60  # 1 минута
        else:
            sleep_time = 1  # 1 секунда

        time_str = f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"
        try:
            bot.send_message(user_id, f"Таймер (работающий): {time_str}")
        except telebot.apihelper.ApiException as e:
            print(f"Ошибка при отправке таймера пользователю {user_id}: {e}")  # Например, пользователь заблокировал бота
            return
        time.sleep(sleep_time)  # Проверять с уменьшающимся интервалом

    # По истечении времени
    if not registered_users[user_id]["solution_sent"]:
        try:
            bot.send_message(user_id,
                             "К сожалению, вы не успели отправить задачу в течение таймера. Чтобы узнать о подробностях, обратитесь в поддержку.")
        except telebot.apihelper.ApiException as e:
            print(f"Ошибка при отправке уведомления об истечении времени пользователю {user_id}: {e}")
    registered_users[user_id]["timer_active"] = False
    save_user_data()


@bot.message_handler(commands=['result'])
def get_result(message):
    if check_timer(message):
        return

    user_id = message.from_user.id
    if user_id not in admin_ids:
        bot.reply_to(message, "У вас нет прав для просмотра этой информации.")
        return
    msg = bot.reply_to(message, "Введите ID пользователя, чтобы получить его решение:")
    bot.register_next_step_handler(msg, process_result_userid)


def process_result_userid(message):
    try:
        user_id = int(message.text)
        if user_id not in registered_users:
            bot.reply_to(message, "Пользователь с таким ID не найден.")
            return

        solution_file = os.path.join(SOLUTION_FOLDER, f"@{bot.get_chat(user_id).username}-result.pdf")
        if os.path.exists(solution_file):
            with open(solution_file, 'rb') as file:
                bot.send_document(message.chat.id, file, caption=f"Решение пользователя ID: {user_id}")
        else:
            bot.reply_to(message, "Решение для этого пользователя не найдено.")
    except ValueError:
        bot.reply_to(message, "Некорректный ID пользователя. Введите число.")
    except telebot.apihelper.ApiException as e:
        print(f"Ошибка при отправке решения пользователю {user_id}: {e}")


@bot.message_handler(content_types=['document'])
def handle_document(message):
    user_id = message.from_user.id

    if user_id not in registered_users or not registered_users[user_id]["registered"]:
        bot.reply_to(message, "Вы не зарегистрированы в олимпиаде. Пожалуйста, зарегистрируйтесь.")
        return

    if registered_users[user_id]["solution_sent"]:
        bot.reply_to(message, "Вы уже отправили решение.")
        return

    if registered_users[user_id]["solution_time"] is None:
        bot.reply_to(message, "Сначала получите задания, чтобы запустить таймер.")
        return

    time_difference = datetime.datetime.now() - registered_users[user_id]["solution_time"]
    if time_difference.total_seconds() > SOLUTION_TIME_LIMIT_SECONDS:
        bot.reply_to(message,
                     "К сожалению, вы не успели отправить задачу в течение таймера. Чтобы узнать о подробностях, обратитесь в поддержку.")
        return

    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        # Ensure the solutions folder exists
        if not os.path.exists(SOLUTION_FOLDER):
            os.makedirs(SOLUTION_FOLDER)

        username = bot.get_chat(user_id).username  # Получение username пользователя

        # Save the file with a unique name based on username
        file_name = f"@{username}-result.pdf"  # Имя файла = username пользователя
        file_path = os.path.join(SOLUTION_FOLDER, file_name)
        with open(file_path, 'wb') as new_file:
            new_file.write(downloaded_file)

        registered_users[user_id]["solution_sent"] = True
        registered_users[user_id]["timer_active"] = False  # Таймер больше не активен
        save_user_data()

        bot.reply_to(message, "Получили вашу работу. Проверяем вашу работу и обязательно сообщим вам. Ждите....")

    except Exception as e:
        bot.reply_to(message, f"Произошла ошибка при обработке файла: {e}")


# --- Обработчик добавления админа ---
@bot.message_handler(commands=['add_admin'])
def add_admin(message):
    user_id = message.from_user.id
    if user_id not in admin_ids:
        bot.reply_to(message, "У вас нет прав для выполнения этой команды.")
        return
    msg = bot.reply_to(message, "Введите ID пользователя, которого хотите сделать админом:")
    bot.register_next_step_handler(msg, process_new_admin_id)


def process_new_admin_id(message):
    try:
        new_admin_id = int(message.text)
        admin_ids.add(new_admin_id)
        save_admin_ids()
        bot.reply_to(message, f"Пользователь с ID {new_admin_id} теперь админ.")
    except ValueError:
        bot.reply_to(message, "Некорректный ID пользователя. Введите число.")


# --- Запуск бота ---
if __name__ == '__main__':
    # Уведомление о начале олимпиады (можно добавить расписание)
    now = datetime.datetime.now()
    if OLYMPIAD_START <= now <= OLYMPIAD_END:  # Проверка, что текущее время в диапазоне олимпиады.
        for user_id in registered_users:
            try:
                bot.send_message(user_id, "Олимпиада началась!")
            except telebot.apihelper.ApiException as e:
                print(f"Ошибка при отправке уведомления о начале олимпиады пользователю {user_id}: {e}")

    bot.polling(none_stop=True)
