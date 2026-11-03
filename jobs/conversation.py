"""Bounded server-side sessions and deterministic month follow-ups; no SQL memory."""
import calendar
import datetime as dt
import re
import secrets
import time
from typing import Any, Callable
from semantic_contracts import requested_period

THAI_MONTHS = ('มกราคม','กุมภาพันธ์','มีนาคม','เมษายน','พฤษภาคม','มิถุนายน',
               'กรกฎาคม','สิงหาคม','กันยายน','ตุลาคม','พฤศจิกายน','ธันวาคม')


class SessionLimit(ValueError):
    pass


class Sessions:
    def __init__(self, clock: Callable[[], float] = time.monotonic, ttl: int = 1800,
                 capacity: int = 128, requests: int = 20) -> None:
        self.clock, self.ttl, self.capacity, self.requests = clock, ttl, capacity, requests
        self.states: dict[str, dict[str, Any]] = {}

    def get(self, token: str | None = None) -> tuple[str, dict[str, Any]]:
        now = self.clock()
        self.states = {k:v for k,v in self.states.items() if now-v['created'] < self.ttl}
        if token not in self.states:
            if len(self.states) >= self.capacity:
                raise SessionLimit('Session capacity reached; please try later')
            token = secrets.token_urlsafe(32)
            self.states[token] = {'created':now, 'requests':0, 'history':[]}
        return token, self.states[token]

    def consume(self, state: dict[str, Any]) -> None:
        if state['requests'] >= self.requests:
            raise SessionLimit(f'This session reached its {self.requests}-question limit; try again after expiry')
        state['requests'] += 1


def followup(question: str, previous: str | None) -> tuple[str, dict[str, Any] | None]:
    text = question.strip().rstrip('?？').strip().lower()
    backwards = text in {'แล้วเดือนก่อนล่ะ','เดือนก่อนล่ะ','แล้วเดือนก่อน','what about the previous month','what about last month'}
    forwards = text in {'แล้วเดือนถัดไปล่ะ','เดือนถัดไปล่ะ','แล้วเดือนถัดไป','what about the next month','what about next month'}
    if not (backwards or forwards):
        # Ambiguous references are never silently treated as independent analytics.
        if re.match(r'^(แล้ว|เทียบกับ|what about|same |those |these )', text):
            raise ValueError('กรุณาระบุคำถามให้ชัดเจน หรือถามต่อว่า “แล้วเดือนก่อนล่ะ” / “แล้วเดือนถัดไปล่ะ”')
        return question, None
    if not previous:
        raise ValueError('ยังไม่มีคำตอบก่อนหน้าสำหรับถามต่อ กรุณาถามโดยระบุเดือนและปีก่อน')
    period = requested_period(previous)
    if not period:
        raise ValueError('คำถามก่อนหน้าต้องมีช่วงเวลาหนึ่งเดือนที่ชัดเจน')
    start, end = map(dt.date.fromisoformat, period)
    next_month = dt.date(start.year+(start.month==12), start.month%12+1, 1)
    if start.day != 1 or end != next_month:
        raise ValueError('ถามต่อแบบเดือนก่อน/ถัดไปได้เฉพาะคำถามช่วงหนึ่งเดือน')
    month_index = start.year*12 + start.month-1 + (-1 if backwards else 1)
    target = dt.date(month_index//12, month_index%12+1, 1)
    target_end = dt.date(target.year+(target.month==12), target.month%12+1, 1)
    replacements = {period[0]:target.isoformat(), period[1]:target_end.isoformat()}
    resolved = re.sub(r'\b\d{4}-\d{2}-\d{2}\b', lambda m:replacements.get(m[0],m[0]), previous)
    for old, new in [(calendar.month_name[start.month],calendar.month_name[target.month]),
                     (THAI_MONTHS[start.month-1],THAI_MONTHS[target.month-1])]:
        resolved = re.sub(re.escape(old)+r'\s+'+str(start.year), new+' '+str(target.year), resolved, flags=re.I)
    if resolved == previous:
        raise ValueError('ไม่สามารถระบุช่วงเดือนเดิมได้ กรุณาเขียนคำถามเต็ม')
    return resolved, {'source':'previous_successful_question','period':[target.isoformat(),target_end.isoformat()]}
