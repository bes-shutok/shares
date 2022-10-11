import csv
import re
from pathlib import Path

from typing import List, Union, Optional, Set

from domain import InciRecord, CasNumber, EcNumber, AnnexRef


def parse_cas(source_str: str) -> Optional[Set[CasNumber]]:
    target_set: Optional[Set[CasNumber]] = None
    if source_str:
        target_set = set()
        result = re.findall(r"\d{2,7}-\d{2}-\d", source_str)
        for cas in set(result):
            target_set.add(CasNumber(cas))

    return target_set


def parse_ec(source_str: str) -> Optional[Set[EcNumber]]:
    target_set: Optional[Set[EcNumber]] = None
    if source_str:
        target_set = set()
        result = re.findall(r"\d{3}-\d{3}-\d", source_str)
        for cas in set(result):
            target_set.add(EcNumber(cas))

    return target_set


def parse_refs(source_str: str) -> Set[AnnexRef]:
    target_set: Set[AnnexRef] = None
    if source_str:
        target_set = set()
        result = re.findall(r"[MDCLXVI]{1,5}/\d{1,4}", source_str)
        for cas in result:
            target_set.add(AnnexRef(cas))

    return target_set


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


def should_skip(refs: Set[AnnexRef]):
    if refs is None:
        return False
    for ref in refs:
        if ref.value.startswith("II/"):
            return True
    return False

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
                name = name.replace("'", "''")
                cas: Set[CasNumber] = parse_cas(row[cas_col])
                ecs: Set[EcNumber] = parse_ec(row[ec_col])
                refs: Set[AnnexRef] = parse_refs(row[ref_col])
                if should_skip(refs):
                    continue
                if name not in names:
                    names.append(name)
                    incis.append(InciRecord(name, cas, ecs, refs))
                else:
                    index: int = names.index(name)
                    if cas is not None:
                        if hasattr(incis[index], "cas"):
                            incis[index].cas.union(cas)
                        else:
                            incis[index].cas = cas

                    if ecs is not None:
                        if hasattr(incis[index], "ecs"):
                            incis[index].ecs.union(ecs)
                        else:
                            incis[index].ecs = ecs

                    if refs is not None:
                        if hasattr(incis[index], "refs"):
                            incis[index].refs.union(refs)
                        else:
                            incis[index].refs = refs

    return incis
