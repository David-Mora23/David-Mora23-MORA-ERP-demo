"""Script para agregar el usuario Gerente a la base de datos existente."""
import sqlite3
import bcrypt
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'erp.db')
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

exists = conn.execute("SELECT id FROM usuarios WHERE email='gerente@erp.com'").fetchone()
if exists:
    print("El usuario gerente@erp.com ya existe en la base de datos.")
else:
    ph = bcrypt.hashpw(b'password123', bcrypt.gensalt()).decode('utf-8')
    conn.execute(
        "INSERT INTO usuarios (email, password_hash, rol) VALUES (?, ?, ?)",
        ('gerente@erp.com', ph, 'Gerente')
    )
    conn.commit()
    print("Usuario gerente@erp.com creado exitosamente con rol Gerente.")

# Mostrar todos los usuarios actuales
print("\nUsuarios registrados:")
for u in conn.execute("SELECT id, email, rol FROM usuarios").fetchall():
    print(f"  [{u['id']}] {u['email']} — {u['rol']}")

conn.close()
