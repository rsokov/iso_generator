try:
    from cStringIO import StringIO as BytesIO
except ImportError:
    from io import BytesIO

import shutil
import pycdlib
import random
import argparse
import os.path
import hashlib
import time

log_file = []


# Парсим аргументы командной строки и присваиваем их значения внутренним переменным
# Аргумент -d, -D, --disk принимает точку монтирования диска(TARGET из findmnt -all)
# Аргумент -u, -U, --usage принимает целое значение желаемого процента заполнения диска от полной емкости
# Далее вызывается функция заполнения диска файлами
def main():
    parser = argparse.ArgumentParser(
        description="Утилита позволяет указать конкретный диск и заполнить его ISO-файлами на указанный процент от объема диска."
                    "Пример использования: python3.9 main.py --disk /mnt/usb1 --usage 3")
    parser.add_argument('-d', '-D', '--disk')
    parser.add_argument('-u', '-U', '--usage')
    args = parser.parse_args()
    # Валидация на отсутствие параметров диска и процента заполнения
    if args.disk is None:
        print("Необходимо указать путь к точке монтирования диска. Используйте параметр -d. Пример: -d /mnt/usb1")
        exit(1)
    if args.usage is None:
        print("Необходимо указать процент заполнения диска. Используйте параметр -u/ Пример: -u 10")
        exit(1)
    # Валидация на предмет существования пути к диску
    if not os.path.exists(args.disk):
        print("Путь", args.disk, "не существует. Проверьте путь к точке монтирования диска.")
        exit(1)
    # Валидация параметра -u на тип данных (принимается только целое число)
    if args.usage.isdigit() != True:
        print("Параметр -u, -U, --usage должен быть целым числом.")
        exit(1)

    # Валидация на границы возможных значений процента заполнения (возможны значения от 0 до 100)
    if 0 <= int(args.usage) <= 100:
        disk_name = args.disk
        usage_percent_goal = int(args.usage)
        fill_disk_by_iso(usage_percent_goal, disk_name)
    else:
        print("Ошибка. Параметр -u, -U, --usage может принимать значения от 0 до 100.")
        exit(1)


# Получаем объем диска, свободное и занятое пространство.
# В цикле выполняем создание ISO-файла и наполнение его рандомным количеством файлов
# За счет рандомного наполнения, размер каждого ISO-файла меняется (не исключены повторы)
# После наполнения ISO-образа файлами, происходит его запись на диск
def fill_disk_by_iso(usage_percent_goal, disk_name):
    i = 0  # Начальное значение счетчика для упорядочивания имен ISO-файлов
    final_iso_list = [] #Начальное состояние списка ISO-файлов
    log_file.append("Путь к диску: " + str(disk_name)) #Пишем путь к диску в лог
    log_file.append("Желаемый процент заполнения: " + str(usage_percent_goal)) #Пишем процент заполнения в лог
    print("Получаю информацию о доступном объеме памяти на диске...") #Вывод текущей операции в консоль
    log_file.append("Получаю информацию о доступном объеме памяти на диске...") #Вывод текущей операции в лог
    total, used, free = get_disk_size(disk_name) # Получаем инфу о полном, доступном и занятом объеме диска
    space_goal_usage = total // 100 * usage_percent_goal # Считаем целевой объем, заданный процентом заполнения
    log_file.append("Общий объем диска: " + str(total) + " КБ") # Вывод в лог общего объема диска
    log_file.append("Занятый объем диска: " + str(used) + " КБ") # Вывод в лог занятого объема диска
    log_file.append("Свободный объем диска: " + str(free) + " КБ") # Вывод в лог свободного объема диска
    print("Генерирую ISO-файлы, вычисляю MD5 и копирую файлы на устройство. Пожалуйста, подождите...") # Вывод текущей операции в консоль
    log_file.append("Генерирую ISO-файлы, вычисляю MD5 и копирую файлы на устройство. Пожалуйста, подождите...")# Вывод текущей операции в лог
    log_file.append("") #Вывод пустой строки в лог для разделения блоков информационных сообщений
    while used < space_goal_usage: # Запуск цикла генерации ISO-файлов
        iso = pycdlib.PyCdlib() # Создание объекта ISO
        iso.new() # Создание нового ISO-файла
        files_quantity = random.randint(100, 10000) # ГСЧ для задания кол-ва файлов в образе ISO
        for w in range(0, files_quantity): # Цикл создания файлов в образе
            textfile = b'test test test\n' # Создание текстового файла с некоторым содержимым
            iso.add_fp(BytesIO(textfile), len(textfile), '/TEST' + str(w) + '.TXT') # Добавление созданного файла в образ
        iso_name = 'new' + str(i) + '.iso' # Генерация имени ISO-файла
        iso.write(iso_name) # Запись ISO-файла с опеределенным именем на диск
        iso.close() # Закрываем работу с файлом
        log_file.append("Создан ISO-файл " + str(iso_name)) # Вывод в лог имени созданного образа
        iso_size = os.path.getsize(iso_name) # Получение размера созданного образа
        log_file.append("Размер ISO-файла " + str(iso_size // 1024) + ' КБ') # Вывод размра образа в лог
        md5_sum = get_md5_checksum(iso_name) # Подсчет MD5 контрольной суммы
        log_file.append("Контрольная сумма MD5: " + str(md5_sum)) # Вывод в лог MD5 контрольной суммы
        final_iso_list.append(iso_name + ' <> ' + str(iso_size // 1024) + ' КБ' + ' <> ' + md5_sum) # Добавляем имя образа, размер и контрольную сумму в список файлов
        log_file.append("Копирую ISO-файл " + str(iso_name) + " на устройство " + str(disk_name)) # Добавляем имя образа, размер и контрольную сумму в лог
        shutil.move(iso_name, os.path.join(disk_name, iso_name)) #Запись образа на внешний носитель
        i = i + 1 # Щелкаем счетчик упорядочивания имен для исключения дублей файлов
        total, used, free = get_disk_size(disk_name) #Получаем актуальный объем свободного и занятого пространства
        log_file.append("")
    print("Операция успешно завершена!") # Сообщение об успешном выполнении операции
    print()
    total, used, free = get_disk_size(disk_name) #Получаем актуальный объем свободного и занятого пространства после завершения цикла генерации файлов
    print("Общий объем диска (КБ):", total) #Вывод обещго объема диска в консоль
    log_file.append("Общий объем диска: " + str(total) + " КБ") #Вывод общего объема диска в лог
    print("Занято на диске (КБ):", used) #Вывод использованного объема диска в консоль
    log_file.append("Занятый объем диска: " + str(used) + " КБ") #Вывод использованного объема диска в консоль
    print("Занятое пространство (%)", int(used * 100 / total)) # Вывод в консоль занятого объема диска в %
    log_file.append("Занятое пространство (%): " + str(int(used * 100 / total))) # Вывод в лог занятого объема диска в %
    print()
    print("Список ISO-файлов:") # Вывод в консоль списка ISO-файлов
    log_file.append("Список ISO-файлов:")#  Вывод в лог списка ISO-файлов
    # Цикла вывода в консоль списка сгенерированных ISO-файлов с именем, размером в КБ и контрольной суммой
    for iso_file in final_iso_list:
        print(iso_file)
        log_file.append(iso_file)

    # Запись лога в текстовый файл
    with open(get_filename_from_date(), 'w') as output:
        for log_item in log_file:
            output.write(str(log_item) + '\n')


# Функция получения доступного, занятого, общего пространства диска
def get_disk_size(disk_name):
    total, used, free = shutil.disk_usage(disk_name)
    total = total // 1024
    used = used // 1024
    free = free // 1024
    return total, used, free


# Вычисляет контрольную сумму MD5
def get_md5_checksum(filename):
    with open(filename, 'rb') as f:
        checksum = hashlib.md5()
        while True:
            data = f.read(2048)
            if not data:
                break
            checksum.update(data)
    f.close()
    return checksum.hexdigest()


# Генерация имени лог-файла на основе текущей даты и времени
def get_filename_from_date():
    current_date = time.strftime("%Y%m%d-%H%M%S")
    filename = "log-" + current_date + ".txt"
    return filename


if __name__ == "__main__":
    main()
