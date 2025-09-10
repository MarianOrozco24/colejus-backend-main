from datetime import datetime

class ValidationError(Exception):
    pass



def register_in_txt(data: str, file_path='logs.txt') -> None:
    txt = f"{datetime.now()}: {data}"
    with open(file_path, "a") as f:
        f.write(txt + "\n")