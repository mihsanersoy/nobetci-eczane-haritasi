import uuid
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import Date, DateTime, Float, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Eczane(Base):
    """
    Türkiye (81 İl) nöbetçi eczane verilerini PostgreSQL'de temsil eden SQLAlchemy 2.0 ORM modeli.
    """
    __tablename__ = "eczaneler"

    # Primary Key (UUID)
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    # Temel Eczane ve Konum Bilgileri
    isim: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    sehir: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    ilce: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    adres: Mapped[str] = mapped_column(Text, nullable=False)
    telefon: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)

    # Harita Koordinatları (Leaflet entegrasyonu için)
    enlem: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    boylam: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Tarih ve Zaman Bilgileri
    nobet_tarihi: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    olusturulma_tarihi: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Bileşik İndeks (Composite Index):
    # Şehir, ilçe ve nöbet tarihine göre yapılan sorguları maksimum hızda çalıştırmak için
    __table_args__ = (
        Index("ix_eczaneler_sehir_ilce_nobet_tarihi", "sehir", "ilce", "nobet_tarihi"),
    )

    def __repr__(self) -> str:
        return (
            f"<Eczane(isim='{self.isim}', sehir='{self.sehir}', "
            f"ilce='{self.ilce}', nobet_tarihi='{self.nobet_tarihi}')>"
        )
