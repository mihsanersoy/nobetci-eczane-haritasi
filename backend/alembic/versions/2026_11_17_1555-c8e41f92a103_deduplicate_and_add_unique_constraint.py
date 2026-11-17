"""deduplicate_and_add_unique_constraint

Revision ID: c8e41f92a103
Revises: 9af7e658d2bb
Create Date: 2026-11-17 15:55:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c8e41f92a103"
down_revision: Union[str, None] = "9af7e658d2bb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Mevcut mükerrer (duplicate) kayıtları temizle:
    # Aynı (isim, sehir, ilce, nobet_tarihi) grubu içinde koordinatı dolu olanı (enlem IS NOT NULL)
    # ve en güncel olanı (rnum = 1) koruyup diğer kopyaları siler.
    op.execute(
        """
        WITH mukerrer_sirali AS (
            SELECT
                id,
                ROW_NUMBER() OVER (
                    PARTITION BY lower(btrim(isim)), lower(btrim(sehir)), lower(btrim(ilce)), nobet_tarihi
                    ORDER BY (enlem IS NOT NULL AND boylam IS NOT NULL) DESC, olusturulma_tarihi DESC, id DESC
                ) AS rnum
            FROM eczaneler
        )
        DELETE FROM eczaneler
        WHERE id IN (
            SELECT id FROM mukerrer_sirali WHERE rnum > 1
        );
        """
    )

    # 2. Harf büyüklüğü veya kenar boşluğu farklarını standartlaştır
    op.execute(
        """
        UPDATE eczaneler
        SET isim = btrim(isim),
            sehir = lower(btrim(sehir)),
            ilce = btrim(ilce);
        """
    )

    # 3. uq_eczane_gunluk_nobet UNIQUE Constraint (Benzersizlik Kısıtlaması) ekle
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'uq_eczane_gunluk_nobet'
            ) THEN
                ALTER TABLE eczaneler
                ADD CONSTRAINT uq_eczane_gunluk_nobet
                UNIQUE (isim, sehir, ilce, nobet_tarihi);
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.drop_constraint("uq_eczane_gunluk_nobet", "eczaneler", type_="unique")
