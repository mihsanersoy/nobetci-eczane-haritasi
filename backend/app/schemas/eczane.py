import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class EczaneBase(BaseModel):
    """
    Eczane verileri için ortak alanları barındıran temel Pydantic şeması.
    """
    isim: str = Field(..., min_length=2, max_length=255, description="Eczanenin adı")
    sehir: str = Field(..., min_length=2, max_length=50, description="Bulunduğu şehir (slug formatında, örn: ankara)")
    ilce: str = Field(..., min_length=2, max_length=100, description="Bulunduğu ilçe")
    adres: str = Field(..., min_length=5, description="Açık adres bilgisi")
    telefon: Optional[str] = Field(None, max_length=30, description="İletişim telefon numarası")
    enlem: Optional[float] = Field(None, ge=-90.0, le=90.0, description="Harita enlem (latitude) koordinatı")
    boylam: Optional[float] = Field(None, ge=-180.0, le=180.0, description="Harita boylam (longitude) koordinatı")
    nobet_tarihi: date = Field(..., description="Nöbetçi olduğu tarih (YYYY-AA-GG)")


class EczaneCreate(EczaneBase):
    """
    Scraper servisi veya yönetim uç noktaları tarafından yeni eczane kaydı
    oluşturulurken kullanılacak şema.
    """
    pass


class EczaneUpdate(BaseModel):
    """
    Mevcut bir eczane kaydını kısmi olarak (PATCH/PUT) güncellemek için kullanılan şema.
    """
    isim: Optional[str] = Field(None, min_length=2, max_length=255)
    sehir: Optional[str] = Field(None, min_length=2, max_length=50)
    ilce: Optional[str] = Field(None, min_length=2, max_length=100)
    adres: Optional[str] = Field(None, min_length=5)
    telefon: Optional[str] = Field(None, max_length=30)
    enlem: Optional[float] = Field(None, ge=-90.0, le=90.0)
    boylam: Optional[float] = Field(None, ge=-180.0, le=180.0)
    nobet_tarihi: Optional[date] = None


class EczaneResponse(EczaneBase):
    """
    API'den Frontend'e (Next.js) dönecek olan yanıt (Response) şeması.
    Veritabanı tarafından üretilen id ve olusturulma_tarihi alanlarını içerir.
    """
    id: uuid.UUID
    olusturulma_tarihi: datetime

    # SQLAlchemy ORM nesnelerinin doğrudan Pydantic modeline dönüştürülmesini sağlar
    model_config = ConfigDict(from_attributes=True)
