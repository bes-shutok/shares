import calendar
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Dict, List, Tuple, Optional, NamedTuple, TypedDict
from unicodedata import name

source_file = Path('./resources', 'incis_example.csv')
destination_file = Path('./resources', 'incis_example.csv')

@dataclass
class CasNumber:
    """A CAS number is a unique identifier for chemical substances."""
    value: str

    def __init__(self, value: str):
        self.value = value

    def __post_init__(self):
        if not self.number:
            raise ValueError("CAS number must not be empty")

@dataclass
class EcNumber:
    """A EC number is a unique identifier for chemical substances."""
    value: str

    def __init__(self, value: str):
        self.value = value

    def __post_init__(self):
        if not self.number:
            raise ValueError("EC number must not be empty")

@dataclass
class Reference:
    """A EU reference for the INCI."""
    value: str

    def __init__(self, value: str):
        self.value = value

    def __post_init__(self):
        if not self.number:
            raise ValueError("Reference must not be empty")

@dataclass
class InciRecord:
    name: str
    cas: Optional[List[CasNumber]]
    ec: Optional[List[EcNumber]]
    refs: Optional[List[Reference]]

    def __init__(self, name: str, cas: Optional[List[CasNumber]], ec: Optional[List[EcNumber]], refs: Optional[List[Reference]]):
        self.name = name
        if cas:
            self.cas = list(cas)
        if ec:
            self.ec = list(ec)
        if refs:
            self.refs = list(refs)

    def __str__(self) -> str:
        return self.__repr__()

    def __repr__(self) -> str:
        result = "('" + self.name + "', "
        if hasattr(self, "cas"):
            result += self.to_sql_array(self.cas) + " "
        else:
            result += "null, "
        if hasattr(self, "ec"):
            result += self.to_sql_array(self.ec) + " "
        else:
            result += "null, "
        if hasattr(self, "refs"):
            result += self.to_sql_array(self.refs) + ")"
        else:
            result += "null)"
        return result
        #'{" 108-47-4"}'::text[], '{"203-586-8"}'::text[], null)"

    def to_sql_array(self, array: List[str]) -> str:
        sql_array: str = "'{"
        for i in range(len(array)):
            if i > 0:
                sql_array += ", "
            sql_array += "\"" + array[i] + "\""
        sql_array += "}', "
        return sql_array

    def __post_init__(self):
        if not self.name:
            raise ValueError("INCI name must not be empty")
