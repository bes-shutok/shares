import os
from typing import Union, List

from domain import InciRecord

HEADER:str = "insert into covalo.inci(inci, cas, ec, refs)\nvalues\n"


def safe_remove_file(path: Union[str, os.PathLike[str]]):
    if os.path.exists(path):
        os.remove(path)


def persist_as_query(path: Union[str, os.PathLike[str]], incis:  List[InciRecord]):
    safe_remove_file(path)
    print("This file will be persisted.")
    print(path)
    f = open(path, "a")
    f.write(HEADER)
    for i, inci in enumerate(incis):
        f.write("       " + str(inci))
        if i < len(incis) - 1:
            f.write(",\n")
        else:
            f.write(";\n")
    f.close()
