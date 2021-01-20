
USING_STRINGS = False
from dataclasses import dataclass, InitVar
from typing import ClassVar
T_CV2 = ClassVar[int]
T_CV3 = ClassVar
T_IV2 = InitVar[int]
T_IV3 = InitVar

@dataclass
class CV():
    T_CV4 = ClassVar
    cv0 = 20
    cv1 = 30

@dataclass
class IV():
    T_IV4 = InitVar
