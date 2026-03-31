# ГЛАВНЫЙ ФАЙЛ
# from parser.t_news_parser import main_t_news_parser
# from parser.news_collector_RBK import main_news_collector_rbk
from json_file.classify_by_ticker import main_classify_by_ticker


# from json_file.work_json import sort_posts_by_date, INPUT_FILE, OUTPUT_FILE,save_posts_with_check

# from parser.t_pulse_parser import sort_posts_by_date


if __name__ == "__main__":
    # main_t_pulse_parser()  # парсим переделываем и сохраняем в json - пульс
    # main_t_news_parser()  # парсим переделываем и сохраняем в json - Т НОВОСТИ
    # main_news_collector_rbk()  # парсим переделываем и сохраняем в json - РБК RSS
    # sort_posts_by_date(input_file=INPUT_FILE, output_file=INPUT_FILE)  # сортируем пост по дате
    main_classify_by_ticker()  # сортировка новости по тикеру
