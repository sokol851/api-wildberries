from sqlalchemy import Column, Float, Integer, String

from app.db import Base


class Product(Base):
    """ Модель продукта """
    __tablename__ = 'products'

    id = Column(Integer,
                primary_key=True,
                index=True)
    artikul = Column(String,
                     unique=True,
                     index=True)
    name = Column(String)
    price = Column(Float)
    rating = Column(Float)
    total_quantity = Column(Integer)
