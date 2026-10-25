import pytest
from pydantic import ValidationError

@pytest.mark.parametrize('price', [5, 10, 15, 20, 25, 30, 35, 100, 1000000])
def test_valid_prices(client, price):
    from server import Item
    assert Item(seller='77', price=price).price == price

@pytest.mark.parametrize('price', [0, -5, 1, 12, 23, 49, 99, 1000001, 10.5])
def test_invalid_prices(client, price):
    from server import Item
    with pytest.raises(ValidationError):
        Item(seller='77', price=price)

def test_sale_rejects_non_multiple_of_five(client):
    from server import Sale
    with pytest.raises(ValidationError):
        Sale(items=[{'seller':'77','price':12}], method='Swish', recipient='Test', payment_confirmed=True)
