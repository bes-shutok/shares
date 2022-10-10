import csv
import re
from pathlib import Path

from typing import List, Union, Optional

from domain import InciRecord


def parse_cas(source_str: str) -> Optional[List[str]]:
    target_list: Optional[List[str]] = None
    if source_str:
        target_list = source_str.split(", ")
        for i in range(len(target_list)):
            target_list[i] = target_list[i].split(" ")[0]

    return target_list


def parse_refs(source_str: str) -> Optional[List[str]]:
    target_list: Optional[List[str]] = None
    if source_str:
        target_list = []
        tokens_list: Optional[List[str]] = source_str.split(" ")

        i = 0
        while i < len(tokens_list):
            if tokens_list[i].startswith("("):
                comment, i = add_comment(i, tokens_list)
                target_list[len(target_list) - 1] += " " + comment
            else:
                target_list.append(tokens_list[i])

            i += 1
    return target_list


def add_comment(i, tokens_list) -> tuple[str, int]:
    if i == 0:
        raise ValueError("Reference must not start with a comment")
    else:
        comment = tokens_list[i]
        if comment.endswith(")"):
            return comment
        i += 1
        if i == len(tokens_list):
            raise ValueError("Reference must end with a comment")
        while not tokens_list[i].endswith(")"):
            comment += " " + tokens_list[i]
            i += 1
            if i == len(tokens_list):
                raise ValueError("Reference must end with a comment")
        comment += " " + tokens_list[i]
        return comment, i + 1


def parse_data(path: Union[str, Path[str]]) -> List[InciRecord]:
    print("This file will be parsed.")
    print(path)

    name_col = "INCI name"
    cas_col = "CAS"
    ec_col = "EC no"
    ref_col = "Annex ref"

    incis: List[InciRecord] = []
    with open(path, 'r') as read_obj:
        csv_dict_reader = csv.DictReader(read_obj)
        names: List[str] = []
        for row in csv_dict_reader:
            if row[name_col] != "":
                name: str = str(row[name_col]).lower()
                result = re.search(r"\b[a-zA-Z]", name)
                char = result.group()
                name = name.replace(char, char.upper(), 1)
                cas: List[str] = parse_cas(row[cas_col])
                ecs: List[str] = parse_cas(row[ec_col])
                refs: List[str] = parse_refs(row[ref_col])
                if name not in names:
                    names.append(name)
                    incis.append(InciRecord(name, cas, ecs, refs))
                else:
                    index: int = names.index(name)
                    incis[index].cas.extend(cas)
                    incis[index].ecs.extend(ecs)
                    incis[index].refs.extend(refs)

    return incis
