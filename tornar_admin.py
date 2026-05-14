"""
Script utilitário: tornar um usuário administrador
Execute após criar sua conta no app:

  python3 tornar_admin.py seu@email.com
"""

import sqlite3
import sys

def tornar_admin(email: str):
    conn = sqlite3.connect("bolao.db")
    cursor = conn.execute(
        "UPDATE usuarios SET is_admin = 1 WHERE email = ?", (email,)
    )
    conn.commit()
    if cursor.rowcount == 0:
        print(f"❌ Usuário '{email}' não encontrado. Cadastre-se no app primeiro.")
    else:
        print(f"✅ '{email}' agora é administrador!")
    conn.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python3 tornar_admin.py felipe89mello@gmail.com")
    else:
        tornar_admin(sys.argv[1])
