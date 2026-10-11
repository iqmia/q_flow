from sqlalchemy import Text

from q_flow.models.cashflow import Cashflow


def test_cashflow_description_uses_text_column():
    assert isinstance(Cashflow.__table__.c.description.type, Text)
