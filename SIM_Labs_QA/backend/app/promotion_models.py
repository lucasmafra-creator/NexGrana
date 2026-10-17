"""Commercial catalog only. No NexGrana user finances or partner credentials."""
from sqlalchemy import String,Text,Integer,Boolean,DateTime,ForeignKey,UniqueConstraint
from sqlalchemy.orm import Mapped,mapped_column
from .db import Base
from .models import uid,now

class PromotionSource(Base):
 __tablename__='promotion_sources'
 id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
 product_id:Mapped[str]=mapped_column(ForeignKey('products.id'),index=True)
 name:Mapped[str]=mapped_column(String(100))
 kind:Mapped[str]=mapped_column(String(30),default='awin_jsonl')
 revision:Mapped[int]=mapped_column(Integer,default=1)
 keywords_json:Mapped[str]=mapped_column(Text,default='[]')
 auto_approve:Mapped[bool]=mapped_column(Boolean,default=False)
 url:Mapped[str]=mapped_column(Text,default='')
 token_env:Mapped[str]=mapped_column(String(100),default='')
 approved_hosts_json:Mapped[str]=mapped_column(Text,default='[]')
 authorization_note:Mapped[str]=mapped_column(Text,default='')
 enabled:Mapped[bool]=mapped_column(Boolean,default=False)
 interval_seconds:Mapped[int]=mapped_column(Integer,default=86400)
 next_run_at:Mapped[object]=mapped_column(DateTime(timezone=True),default=now)
 lease_until:Mapped[object|None]=mapped_column(DateTime(timezone=True),nullable=True)
 lease_token:Mapped[str]=mapped_column(String(36),default='')
 last_status:Mapped[str]=mapped_column(String(30),default='NOT_CONFIGURED')
 last_run_at:Mapped[object|None]=mapped_column(DateTime(timezone=True),nullable=True)
 last_error:Mapped[str]=mapped_column(String(200),default='')

class PromotionOffer(Base):
 __tablename__='promotion_offers'
 __table_args__=(UniqueConstraint('product_id','origin_key',name='uq_promotion_origin'),)
 id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
 product_id:Mapped[str]=mapped_column(ForeignKey('products.id'),index=True)
 source_id:Mapped[str|None]=mapped_column(ForeignKey('promotion_sources.id'),nullable=True)
 origin_key:Mapped[str]=mapped_column(String(300))
 payload_json:Mapped[str]=mapped_column(Text)
 content_sha256:Mapped[str]=mapped_column(String(64))
 status:Mapped[str]=mapped_column(String(30),default='draft')
 revision:Mapped[int]=mapped_column(Integer,default=1)
 approved_sha256:Mapped[str]=mapped_column(String(64),default='')
 updated_at:Mapped[object]=mapped_column(DateTime(timezone=True),default=now)

class PromotionRun(Base):
 __tablename__='promotion_runs'
 id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
 product_id:Mapped[str]=mapped_column(ForeignKey('products.id'),index=True)
 source_id:Mapped[str]=mapped_column(ForeignKey('promotion_sources.id'))
 status:Mapped[str]=mapped_column(String(30))
 created_count:Mapped[int]=mapped_column(Integer,default=0)
 updated_count:Mapped[int]=mapped_column(Integer,default=0)
 skipped_count:Mapped[int]=mapped_column(Integer,default=0)
 reason:Mapped[str]=mapped_column(String(200),default='')
 payload_sha256:Mapped[str]=mapped_column(String(64),default='')
 created_at:Mapped[object]=mapped_column(DateTime(timezone=True),default=now)

class PromotionControl(Base):
 __tablename__='promotion_control'
 key:Mapped[str]=mapped_column(String(40),primary_key=True)
 next_dispatch_at:Mapped[object]=mapped_column(DateTime(timezone=True),default=now)
