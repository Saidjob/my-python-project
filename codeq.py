
import telebot
from telebot import types
import datetime
import time
import os
from threading import Thread
from random import randint
import bcrypt
import logging

# --- Настройки ---
BOT_TOKEN = "YOUR_BOT_TOKEN"  # Замените на токен вашего бота
REGISTER_PASSWORD_HASH = bcrypt.hashpw("REGISTER_PASSWORD".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
TASKS_FILE_PATH = "Olympiada/olympiad.pdf"
OLYMPIAD_START = datetime.datetime(2025, 3, 4, 8, 0, 0)
OLYMPIAD_END = datetime.datetime(2025, 3, 8, 8, 0, 0)
SOLUTION_TIME_LIMIT_SECONDS = 60 * 60
SOLUTION_FOLDER = "solutions"
USER_DATA_FILE = "user_data.txt"
ADMIN_IDS_FILE = "admin_ids.txt"
ORGANIZATOR_USERNAME = "erkinzodsaidjon"

# --- Настройка логирования ---
logging.basicConfig(filename='bot.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Инициализация бота ---
bot = telebot.TeleBot(BOT_TOKEN)

# --- Данные в памяти ---
registered_users = {}  # {user_id: {"code": str, "registered": bool, "solution_sent": bool, "solution_time": datetime, "timer_active": bool, "username_checked": bool, "points": int}}
admin_ids = set()


# --- Функция загрузки данных пользователей из файла ---
def load_user_data():
    global registered_users
    try:
        with open(USER_DATA_FILE, "r") as f:
            for line in f:
                values = line.strip().split(",")
                if len(values) == 8:
                    user_id, code, registered, solution_sent, solution_time, timer_active, username_checked, points = values
                elif len(values) == 7:  # Обработка старых записей
                    user_id, code, registered, solution_sent, solution_time, timer_active, username_checked = values
                    points = "0"  # Значение по умолчанию для старых записей
                elif len(values) == 6:
                    user_id, code, registered, solution_sent, solution_time, timer_active = values
                    username_checked = "False"
                    points = "0"
                else:
                    print(f"Неверный формат строки в user_data.txt: {line}")
                    continue

                registered_users[int(user_id)] = {
                    "code": code,
                    "registered": registered == "True",
                    "solution_sent": solution_sent == "True",
                    "solution_time": datetime.datetime.fromisoformat(
                        solution_time) if solution_time != "None" else None,
                    "timer_active": timer_active == "True",
                    "username_checked": username_checked == "True",
                    "points": int(points)  # Добавлено поле баллов
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
                    f"{user_id},{data['code']},{data['registered']},{data['solution_sent']},{data['solution_time']},{data['timer_active']},{data['username_checked']},{data['points']}\n")
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
    while any(user.get("code") == code for user in registered_users.values()):
        code = str(randint(10000, 99999))
    return code


# --- Функция для форматирования времени до конца олимпиады ---
def format_timedelta(delta):
    days = delta.days
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{days} дней, {hours} часов, {minutes} минут, {seconds} секунд"


# --- Проверка, активен ли таймер ---
def check_timer(message):
    user_id = message.from_user.id
    if user_id in registered_users and registered_users[user_id]["timer_active"]:
        if message.text == "/help":
            return False
        else:
            return True  # Блокируем все команды, кроме /help
    return False

# --- Обработчики команд ---
@bot.message_handler(commands=['start'])
def start(message):
    if check_timer(message):
        bot.reply_to(message, "Во время решения олимпиады вам доступна только команда /help.")
        return
    user_id = message.from_user.id
    username = message.from_user.username
    bot.reply_to(message,
                 f"Привет, {username}. Рад видеть тебя на этой олимпиаде. Чтобы участвовать в олимпиаде, нажмите /register для регистрации.")


@bot.message_handler(commands=['help'])
def help(message):
    bot.reply_to(message)


@bot.message_handler(commands=['register'])
def register(message):
    if check_timer(message):
        bot.reply_to(message, "Во время решения олимпиады вам доступна только команда /help.")
        return

    user_id = message.from_user.id
    if user_id in registered_users and registered_users[user_id]["registered"]:
        bot.reply_to(message, "Вы уже зарегистрированы в олимпиаде.")
        return

    # Проверка наличия username
    if message.from_user.username is None:
        bot.reply_to(message, "Для регистрации в олимпиаде вам необходимо создать @username в Telegram.\n"
                             "Инструкция:\n"
                             "1. Откройте Telegram.\n"
                             "2. Перейдите в 'Настройки'.\n"
                             "3. Найдите поле 'Имя пользователя' и задайте его.")
        registered_users[user_id] = {"code": None, "registered": False, "solution_sent": False,
                                     "solution_time": None, "timer_active": False, "username_checked": False,
                                     "points": 0}
        save_user_data()
        return

    msg = bot.reply_to(message, "Введите пароль, который дал организатор:")
    bot.register_next_step_handler(msg, process_register_password)


def process_register_password(message):
    user_id = message.from_user.id
    password = message.text
    if bcrypt.checkpw(password.encode('utf-8'), REGISTER_PASSWORD_HASH.encode('utf-8')):
        code = generate_unique_code()
        registered_users[user_id] = {"code": code, "registered": True, "solution_sent": False,
                                     "solution_time": None, "timer_active": False,
                                     "username_checked": True, "points": 0}
        save_user_data()
        bot.reply_to(message,
                     f"Вы успешно зарегистрировались в этой олимпиаде. Ваш уникальный код: {code}. Чтобы узнать о статусе периода олимпиады нажмите /stat. Для подробной информации и поддержки используйте /help.")
    else:
        bot.reply_to(message, "Пароль неверный. Проверьте пароль и попробуйте еще раз.")
        msg = bot.reply_to(message, "Введите пароль, который дал организатор:")
        bot.register_next_step_handler(msg, process_register_password)


@bot.message_handler(commands=['stat'])
def stat(message):
    if check_timer(message):
        bot.reply_to(message, "Во время решения олимпиады вам доступна только команда /help.")
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
                         time_left) + ". Чтобы получит задачи, нажмите /get_tasks. У вас будет ровно 1 час чтобы отправит решение (в формате pdf; ОБЯЗАТЕЛЬНО).")
    else:
        bot.reply_to(message,
                     "Период олимпиады уже закончилась. Чтобы узнать о подробностях обратитесь к поддержку /help")


@bot.message_handler(commands=['registered_users'])
def registered_users_list(message):
    if message.from_user.username == ORGANIZATOR_USERNAME:
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
        bot.reply_to(message, "У вас нет прав для просмотра этой информации.")


@bot.message_handler(commands=['delete_users'])
def delete_users(message):
    if message.from_user.username == ORGANIZATOR_USERNAME:
        msg = bot.reply_to(message,
                           "Чтобы удалить участника олимпиады, отправьте username участников, которых хотите удалить из олимпиады (каждый username на новой строке):")
        bot.register_next_step_handler(msg, process_delete_users)
    else:
        bot.reply_to(message, "У вас нет прав для выполнения этой команды.")


def process_delete_users(message):
    usernames = message.text.splitlines()
    deleted_count = 0
    for username in usernames:
        for user_id, data in list(registered_users.items()):
            try:
                user_obj = bot.get_chat(user_id)
                if user_obj.username == username.replace("@", ""):
                    del registered_users[user_id]
                    deleted_count += 1
                    save_user_data()
                    break
            except telebot.apihelper.ApiException as e:
                print(f"Не удалось получить информацию о пользователе {user_id}: {e}")
    bot.reply_to(message, f"Удалено {deleted_count} пользователей.")


@bot.message_handler(commands=['get_tasks'])
def get_tasks(message):
    if check_timer(message):
        bot.reply_to(message, "Во время решения олимпиады вам доступна только команда /help.")
        return

    user_id = message.from_user.id
    if user_id not in registered_users or not registered_users[user_id]["registered"]:
        bot.reply_to(message,
                     "Вы не зарегистрированы в олимпиаде. Пожалуйста, зарегистрируйтесь с помощью команды /register.")
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
            registered_users[user_id]["timer_active"] = True
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
        if not registered_users[user_id]["timer_active"]:
            return

        remaining_time = end_time - datetime.datetime.now()
        hours, remainder = divmod(remaining_time.total_seconds(), 3600)
        minutes, seconds = divmod(remainder, 60)

        if remaining_time.total_seconds() > 600:
            sleep_time = 600
        elif remaining_time.total_seconds() > 60:
            sleep_time = 60
        else:
            sleep_time = 1

        time_str = f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"
        try:
            bot.send_message(user_id, f"Таймер (работающий): {time_str}")
        except telebot.apihelper.ApiException as e:
            print(f"Ошибка при отправке таймера пользователю {user_id}: {e}")
            return
        time.sleep(sleep_time)

    if not registered_users[user_id]["solution_sent"]:
        try:
            bot.send_message(user_id,
                             "К сожалению, вы не успели отправить задачу в течение таймера. Чтобы узнать о подробностях, обратитесь в поддержку.")
        except telebot.apihelper.ApiException as e:
            print(f"Ошибка при отправке уведомления об истечении времени пользователю {user_id}: {e}")
    registered_users[user_id]["timer_active"] = False
    save_user_data()


@bot.message_handler(commands=['results'])
def results(message):
    if message.from_user.username == ORGANIZATOR_USERNAME:
        users_with_solutions = {user_id: data['code'] for user_id, data in registered_users.items() if
                                data['solution_sent']}

        if not users_with_solutions:
            bot.reply_to(message, "Никто еще не отправил решения.")
            return

        codes_list = "\n".join(f"Код: {code}" for code in users_with_solutions.values())
        bot.reply_to(message, f"Список кодов участников, отправивших решения:\n{codes_list}\n\n"
                             "Чтобы посмотреть решение участника, отправьте его индивидуальный код:")
        bot.register_next_step_handler(message, process_solution_code)
    else:
        bot.reply_to(message, "У вас нет прав для выполнения этой команды.")


def process_solution_code(message):
    code = message.text
    user_id = None
    for u_id, data in registered_users.items():
        if data['code'] == code and data['solution_sent']:
            user_id = u_id
            break

    if user_id is None:
        bot.reply_to(message, "Неверный код или участник не отправлял решение.")
        return

    try:
        solution_file = os.path.join(SOLUTION_FOLDER, f"@{bot.get_chat(user_id).username}-result.pdf")
        if os.path.exists(solution_file):
            with open(solution_file, 'rb') as file:
                bot.send_document(message.chat.id, file, caption=f"Решение пользователя с кодом: {code}")
        else:
            bot.reply_to(message, "Решение для этого пользователя не найдено.")
    except ValueError:
        bot.reply_to(message, "Некорректный ID пользователя. Введите число.")
    except telebot.apihelper.ApiException as e:
        print(f"Ошибка при отправке решения пользователю {user_id}: {e}")
    except Exception as e:
        logging.error(f"Error processing solution code: {e}")
        bot.reply_to(message, f"Произошла ошибка при обработке запроса: {e}")


@bot.message_handler(commands=['result_olymp'])
def result_olymp(message):
    if message.from_user.username == ORGANIZATOR_USERNAME:
        users_list = "\n".join(
            f"Код: {data['code']}, Username: @{bot.get_chat(user_id).username}" for user_id, data in
            registered_users.items() if data['registered'])
        bot.reply_to(message, f"Список участников:\n{users_list}\n\n"
                             "Чтобы добавить баллы участника, отправьте данные следующим образом:\n"
                             "@username - [20] балл")
        bot.register_next_step_handler(message, process_add_points)
    else:
        bot.reply_to(message, "У вас нет прав для выполнения этой команды.")


def process_add_points(message):
    try:
        text = message.text
        username = text.split(" - ")[0].replace("@", "")
        points = int(text.split("[")[1].split("]")[0])

        user_id = None
        for u_id in registered_users:
            try:
                if bot.get_chat(u_id).username == username:
                    user_id = u_id
                    break
            except:
                pass

        if user_id is None:
            bot.reply_to(message, "Пользователь с таким username не найден.")
            return

        registered_users[user_id]["points"] = points  # Сохраняем баллы
        save_user_data()  # Сохраняем данные в файл

        bot.reply_to(message, f"Баллы для пользователя @{username} успешно добавлены: {points}")

    except Exception as e:
        bot.reply_to(message, f"Ошибка формата. Пример: @username - [20] балл")
        logging.error(f"Error processing add points: {e}")


@bot.message_handler(commands=['list_balls'])
def list_balls(message):
    if message.from_user.username == ORGANIZATOR_USERNAME:
        users_with_points = "\n".join(
            f"@{bot.get_chat(user_id).username} - {data['points']} балл(ов)"
            for user_id, data in registered_users.items() if data['points'] > 0
        )
        if users_with_points:
            bot.reply_to(message, f"Список участников с баллами:\n{users_with_points}")
        else:
            bot.reply_to(message, "Пока нет участников с баллами.")
    else:
        bot.reply_to(message, "У вас нет прав для выполнения этой команды.")


@bot.message_handler(content_types=['document'])
def handle_document(message):
    user_id = message.from_user.id
    now = datetime.datetime.now()

    # Проверяем, находится ли текущее время в диапазоне проведения олимпиады
    if not (OLYMPIAD_START <= now <= OLYMPIAD_END):
        bot.reply_to(message, "Сейчас не время для отправки решений. Пожалуйста, дождитесь начала/окончания олимпиады.")
        return

    if user_id not in registered_users or not registered_users[user_id]["registered"]:
        bot.reply_to(message, "Вы не зарегистрированы в олимпиаде. Пожалуйста, зарегистрируйтесь.")
        return

    # Проверяем, активен ли таймер у пользователя (только во время активного таймера разрешаем прием файлов)
    if user_id in registered_users and registered_users[user_id]["timer_active"]:
        # Дополнительная проверка на формат файла (PDF)
        if message.document.file_name.endswith(".pdf"):
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
                registered_users[user_id]["timer_active"] = False
                save_user_data()
                return

            try:
                file_info = bot.get_file(message.document.file_id)
                downloaded_file = bot.download_file(file_info.file_path)

                # Ensure the solutions folder exists
                if not os.path.exists(SOLUTION_FOLDER):
                    os.makedirs(SOLUTION_FOLDER)

                username = bot.get_chat(user_id).username  # Получение username пользователя
                solution_start_time = registered_users[user_id]["solution_time"]  # Запоминаем время начала решения

                # Save the file with a unique name based on username
                file_name = f"@{username}-result.pdf"  # Имя файла = username пользователя
                file_path = os.path.join(SOLUTION_FOLDER, file_name)
                with open(file_path, 'wb') as new_file:
                    new_file.write(downloaded_file)

                registered_users[user_id]["solution_sent"] = True
                registered_users[user_id]["timer_active"] = False
                save_user_data()

                solution_time = datetime.datetime.now() - solution_start_time
                solution_time_str = str(solution_time).split(".")[0]  # Убираем микросекунды

                bot.reply_to(message,
                             f"Получили вашу работу. Проверяем вашу работу и обязательно сообщим вам. Вы решали задачу в течение {solution_time_str}.")

            except Exception as e:
                bot.reply_to(message, f"Произошла ошибка при обработке файла: {e}")
                registered_users[user_id]["timer_active"] = False
                save_user_data()
        else:
            bot.reply_to(message, "Пожалуйста, отправьте решение в формате PDF.")
    else:
        bot.reply_to(message, "Сначала получите задания и начните выполнение, чтобы отправить решение.")
        return

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


# --- Обработчик всех текстовых сообщений (для блокировки команд во время таймера) ---
@bot.message_handler(func=lambda message: True, content_types=['text'])
def echo_all(message):
    if check_timer(message):
        bot.reply_to(message, "Во время решения олимпиады вам доступна только команда /help.")
        return

# --- Запуск бота ---
if __name__ == '__main__':
    # Уведомление о начале олимпиады (можно добавить расписание)
    now = datetime.datetime.now()
    if OLYMPIAD_START <= now <= OLYMPIAD_END:
        for user_id in registered_users:
            try:
                bot.send_message(user_id, "Олимпиада началась!")
            except telebot.apihelper.ApiException as e:
                print(f"Ошибка при отправке уведомления о начале олимпиады пользователю {user_id}: {e}")

    bot.polling(none_stop=True)
