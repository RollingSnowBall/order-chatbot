import sqlite3
import chromadb
from sentence_transformers import SentenceTransformer
import uuid

#INSERT INTO "main"."MENU_PRICE" ("MENU_ID", "MENU_SIZE", "MENU_PRICE")VALUES ('000002', 'TALL', 6800);
#INSERT INTO "main"."MENU_PRICE" ("MENU_ID", "MENU_SIZE", "MENU_PRICE")VALUES ('000002', 'GRANDE', 7100);
#INSERT INTO "main"."MENU_PRICE" ("MENU_ID", "MENU_SIZE", "MENU_PRICE")VALUES ('000002', 'VENTI', 8400);

try:
    conn = sqlite3.connect("C://PROJECT//data//cafe_juno.db")
    print("DB 연결 성공!")
    cursor = conn.cursor()

    # 쿼리 실행
    query = "SELECT A.MENU_ID, A.MENU_NM, B.MENU_SIZE, B.MENU_PRICE FROM MENU_INFO A, MENU_PRICE B WHERE A.MENU_ID = B.MENU_ID"
    cursor.execute(query)

    # 결과 출력
    results = cursor.fetchall()
    print("쿼리 결과:")
    if results:
        for row in results:
            menu_id, menu_nm, menu_size, menu_price = row
            print(f"MENU_ID: {menu_id}, MENU_NM: {menu_nm}, MENU_SIZE: {menu_size}, MENU_PRICE: {menu_price}원")
    else:
        print("결과가 없습니다. 테이블 확인 필요.")
except sqlite3.Error as e:
    print(f"DB 오류: {e}")
finally:
    conn.close()
    print("DB 연결 종료.")