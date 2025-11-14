from sqlalchemy import (
    Column,
    Integer,
    Text,
    Float,
    String,
    ForeignKey,
    DateTime,
    LargeBinary
)
from sqlalchemy.orm import relationship
from .db_config import Base


class Paciente(Base):
    __tablename__ = "paciente"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(Text, nullable=False)
    idade = Column(Integer)
    peso = Column(Float)
    altura = Column(Float)
    genero = Column(String(10))

    # relacionamento com coletas
    coletas = relationship(
        "Coleta",
        back_populates="paciente",
        cascade="all, delete"
    )


class Coleta(Base):
    __tablename__ = "coletas"

    id = Column(Integer, primary_key=True, index=True)
    paciente_id = Column(Integer, ForeignKey("paciente.id", ondelete="CASCADE"))

    data_coleta = Column(DateTime)
    dados_emg = Column(LargeBinary)      # bytea
    grafico_emg = Column(LargeBinary)    # bytea
    video_path = Column(Text)
    relatorio_pdf = Column(LargeBinary)  # bytea

    paciente = relationship("Paciente", back_populates="coletas")
