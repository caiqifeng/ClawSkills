# coding=utf-8
from log_list_query import get_log_list, print_summary, save_excel


if __name__ == "__main__":
    payload, data = get_log_list(
        project="jxsj4",
        fromtime="2026-04-28",
        totime="2026-04-30",
        levels=["Exception"],
        log_string="",
        size=500,
        limit=500,
        timeout=120,
    )
    print_summary(payload, data, max_rows=20)
    excel_path = save_excel(payload, data)
    print()
    print("Excel附件：{}".format(excel_path))
