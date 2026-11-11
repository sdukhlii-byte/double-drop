from quest import Case

from .double_drop import CASE as DOUBLE_DROP

CASES: dict[str, Case] = {DOUBLE_DROP.id: DOUBLE_DROP}
DEFAULT_CASE_ID = DOUBLE_DROP.id
