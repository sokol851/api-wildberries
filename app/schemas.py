from pydantic import BaseModel


class ProductCreate(BaseModel):
    """ Схема продукта при создании """
    artikul: str


class ProductBase(BaseModel):
    """ Базовая схема продукта"""
    name: str
    artikul: str
    price: float
    rating: float
    total_quantity: int

    class Config:
        from_attributes = True
