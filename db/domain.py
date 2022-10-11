from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Set

source_file = Path('./resources', 'incis_example.csv')
destination_file = Path('./resources', 'incis_example.csv')


@dataclass
class CasNumber:
    """A CAS number is a unique identifier for chemical substances."""
    value: str

    def __init__(self, value: str):
        self.value = value

    def __post_init__(self):
        if not self.value:
            raise ValueError("CAS number must not be empty")

    def __eq__(self, o: object) -> bool:
        if isinstance(o, CasNumber):
            return self.value == o.value
        return False

    def __hash__(self) -> int:
        return self.value.__hash__()

    def __str__(self) -> str:
        return self.__repr__()

    def __repr__(self) -> str:
        return self.value


@dataclass
class EcNumber:
    """A EC number is a unique identifier for chemical substances."""
    value: str

    def __init__(self, value: str):
        self.value = value

    def __post_init__(self):
        if not self.value:
            raise ValueError("EC number must not be empty")

    def __eq__(self, o: object) -> bool:
        if isinstance(o, EcNumber):
            return self.value == o.value
        return False

    def __hash__(self) -> int:
        return self.value.__hash__()

    def __str__(self) -> str:
        return self.__repr__()

    def __repr__(self) -> str:
        return self.value


@dataclass
class AnnexRef:
    """A EU reference for the INCI."""
    value: str

    def __init__(self, value: str):
        self.value = value

    def __post_init__(self):
        if not self.value:
            raise ValueError("Reference must not be empty")

    def __eq__(self, o: object) -> bool:
        if isinstance(o, AnnexRef):
            return self.value == o.value
        return False

    def __hash__(self) -> int:
        return self.value.__hash__()

    def __str__(self) -> str:
        return self.__repr__()

    def __repr__(self) -> str:
        return self.value


@dataclass
class InciRecord:
    name: str
    cas: Optional[Set[CasNumber]]
    ecs: Optional[Set[EcNumber]]
    refs: Optional[Set[AnnexRef]]

    def __init__(self, name: str, cas: Set[CasNumber], ecs: Set[EcNumber], refs: Set[AnnexRef]):
        self.name = name
        if cas:
            self.cas = cas
        if ecs:
            self.ecs = ecs
        if refs:
            self.refs = refs

    def __str__(self) -> str:
        return self.__repr__()

    def __repr__(self) -> str:
        result = "('" + self.name + "', "
        if hasattr(self, "cas"):
            result += self.to_sql_array(self.cas) + ", "
        else:
            result += "null, "
        if hasattr(self, "ecs"):
            result += self.to_sql_array(self.ecs) + ", "
        else:
            result += "null, "
        if hasattr(self, "refs"):
            result += self.to_sql_array(self.refs) + ")"
        else:
            result += "null)"
        return result

    @staticmethod
    def to_sql_array(values: Set[any]) -> str:
        sql_array: str = "'{"
        i = 0
        for value in values:
            if i > 0:
                sql_array += ", "
            sql_array += "\"" + str(value) + "\""
            i += 1
        sql_array += "}'"
        return sql_array

    def __post_init__(self):
        if not self.name:
            raise ValueError("INCI name must not be empty")
