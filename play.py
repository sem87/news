# from json_file.work_json import sort_posts_by_date
from parser.t_news_parser import main_t_news_parser
from parser.t_pulse_parser import sort_posts_by_date


if __name__ == "__main__":
    # main_t_pulse_parser()  # парсим переделываем и сохраняем в json - пульс
    main_t_news_parser()  # парсим переделываем и сохраняем в json - Т НОВОСТИ
    sort_posts_by_date()  # сортируем пост по дате
