import sqlite3
import chromadb
from sentence_transformers import SentenceTransformer
import uuid

conn = sqlite3.connect("menu.db")
cursor = conn.cursor()