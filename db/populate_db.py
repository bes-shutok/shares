from pathlib import Path
from typing import List
from db import source_file, destination_file

from db.domain import InciRecord

from db.parsing import parse_data


def main():
    print("Starting conversion from " + str(source_file) + " to " + str(destination_file))

    incis: List[InciRecord] = parse_data(source_file)
    #persist_as_query(destination_file, incis)


if __name__ == "__main__":
    main()
