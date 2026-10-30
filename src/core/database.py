"""
database.py – Lưu trữ lịch sử, thống kê và sự kiện hệ thống (SQLite + SQLAlchemy)
"""
import logging
import threading
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.orm import DeclarativeBase, Session
from config import DB_CONFIG

logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

class PhaseLog(Base):
    __tablename__ = 'phase_log'
    id        = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    direction = Column(String(10))
    color     = Column(String(10))
    duration  = Column(Float)
    mode      = Column(String(20))

class VehicleCount(Base):
    __tablename__ = 'vehicle_count'
    id        = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    north     = Column(Integer, default=0)
    south     = Column(Integer, default=0)
    east      = Column(Integer, default=0)
    west      = Column(Integer, default=0)

class EventLog(Base):
    __tablename__ = 'event_log'
    id        = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    level     = Column(String(10))
    message   = Column(Text)

class Database:
    def __init__(self):
        self._lock = threading.Lock()
        db_path = DB_CONFIG['PATH']
        import os; os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._engine = create_engine(f'sqlite:///{db_path}', echo=False)
        Base.metadata.create_all(self._engine)
        logger.info(f"Database: khởi tạo OK tại {db_path}")

    def log_phase(self, direction: str, color: str, duration: float, mode: str):
        with self._lock:
            with Session(self._engine) as s:
                s.add(PhaseLog(direction=direction, color=color, duration=duration, mode=mode))
                s.commit()

    def log_vehicles(self, counts: dict):
        with self._lock:
            with Session(self._engine) as s:
                s.add(VehicleCount(
                    north=counts.get('NORTH', 0), south=counts.get('SOUTH', 0),
                    east=counts.get('EAST', 0),  west=counts.get('WEST', 0)
                ))
                s.commit()

    def log_event(self, level: str, message: str):
        with self._lock:
            with Session(self._engine) as s:
                s.add(EventLog(level=level, message=message))
                s.commit()

    def get_vehicle_history(self, minutes: int = 60) -> list:
        since = datetime.utcnow() - timedelta(minutes=minutes)
        with Session(self._engine) as s:
            rows = s.query(VehicleCount).filter(VehicleCount.timestamp >= since).order_by(VehicleCount.timestamp).all()
            return [{'time': r.timestamp.strftime('%H:%M:%S'), 'north': r.north,
                     'south': r.south, 'east': r.east, 'west': r.west} for r in rows]

    def get_phase_history(self, limit: int = 50) -> list:
        with Session(self._engine) as s:
            rows = s.query(PhaseLog).order_by(PhaseLog.timestamp.desc()).limit(limit).all()
            return [{'time': r.timestamp.strftime('%H:%M:%S'), 'direction': r.direction,
                     'color': r.color, 'duration': r.duration, 'mode': r.mode} for r in rows]

    def get_events(self, limit: int = 30) -> list:
        with Session(self._engine) as s:
            rows = s.query(EventLog).order_by(EventLog.timestamp.desc()).limit(limit).all()
            return [{'time': r.timestamp.strftime('%H:%M:%S'), 'level': r.level,
                     'message': r.message} for r in rows]

    def cleanup_old(self):
        cutoff = datetime.utcnow() - timedelta(days=DB_CONFIG['MAX_HISTORY_DAYS'])
        with self._lock:
            with Session(self._engine) as s:
                s.query(PhaseLog).filter(PhaseLog.timestamp < cutoff).delete()
                s.query(VehicleCount).filter(VehicleCount.timestamp < cutoff).delete()
                s.query(EventLog).filter(EventLog.timestamp < cutoff).delete()
                s.commit()
