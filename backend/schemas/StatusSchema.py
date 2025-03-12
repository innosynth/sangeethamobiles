from sqlalchemy import Column, String, Text, DateTime, Float, ForeignKey, func
import enum

class StatusEnum(enum.IntEnum):
    ACTIVE = 1
    INACTIVE = 0
    PENDING = -1
    FAILURE = -2