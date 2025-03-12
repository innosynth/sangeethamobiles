import logging

from sqlalchemy import create_engine, Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
load_dotenv()



DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
