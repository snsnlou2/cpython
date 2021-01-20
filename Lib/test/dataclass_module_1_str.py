
from __future__ import annotations
USING_STRINGS = True
import dataclasses
import typing
T_CV2 = typing.ClassVar[int]
T_CV3 = typing.ClassVar
T_IV2 = dataclasses.InitVar[int]
T_IV3 = dataclasses.InitVar

@dataclasses.dataclass
class CV():
    T_CV4 = typing.ClassVar
    cv0 = 20
    cv1 = 30

@dataclasses.dataclass
class IV():
    T_IV4 = dataclasses.InitVar
