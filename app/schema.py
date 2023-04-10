from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import  relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Owner(Base):
    __tablename__ = 'owners'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    email = Column(String)

class Repo(Base):
    __tablename__ = 'repos'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    status = Column(String)
    stars_count = Column(Integer)
    owner_id = Column(Integer, ForeignKey('owners.id'))
    owner = relationship(Owner, backref='repos')