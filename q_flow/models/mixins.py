from sqlalchemy import Column, DateTime, String, func
from sqlalchemy.ext.declarative import declared_attr
from q_flow.extensions import db
from q_flow.services.utils import gen_id

class BaseMixin:
    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    id = Column(String(64), primary_key=True, default=gen_id)
    created_at = Column(DateTime, default=func.now())
    created_by = Column(String(50), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    updated_by = Column(String(50))
    timestamp = Column(DateTime, default=func.now(), onupdate=func.now())
    is_deleted = Column(db.Boolean, default=False)

    @classmethod
    def Identify(cls, id):
        if not id:
            return None
        return cls.query.get(id)

    def add(self):
        db.session.add(self)
        return self

    def commit(self):
        db.session.add(self)
        db.session.commit()
        return self

    def update(self, user_id, **kwargs):
        for key in self.__table__.columns.keys():
            value = kwargs.get(key, getattr(self, key))
            setattr(self, key, value)
        self.updated_by = user_id
        self.updated_at = func.now()
        self.commit()
        return self

    def from_dict(self, data, user_id):
        for key in self.__table__.columns.keys():
            value = data.get(key, getattr(self, key))
            setattr(self, key, value)
        self.id = gen_id()
        self.created_by = user_id
        self.updated_by = user_id
        return self

    def delete(self):
        self.is_deleted = True
        self.commit()

    def hard_delete(self):
        db.session.delete(self)
        db.session.commit()

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def __str__(self):
        return str(self.as_dict())

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.as_dict()}>"

