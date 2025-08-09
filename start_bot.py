import sqlite3
import chromadb
from sentence_transformers import SentenceTransformer
import uuid
import os
import chromadb.utils.embedding_functions as embedding_functions
from openai import OpenAI

from dotenv import load_dotenv

# 텔레메트리 비활성화
os.environ["CHROMA_TELEMETRY"] = "false"

# OpenAI API 키 설정 (환경 변수에서 가져오거나 직접 입력)
load_dotenv()

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# 한국어 특화 Sentence-Transformers 모델 로드
embedder = SentenceTransformer('jhgan/ko-sroberta-multitask')

# ChromaDB 클라이언트 초기화: 데이터베이스와 연결할 클라이언트 객체를 생성합니다.
chroma_client = chromadb.Client()

# 사용할 컬렉션(데이터 그룹)의 이름을 지정합니다.
collection_name = "juno-cafe"

# 임베딩 함수 정의: 문장을 벡터로 변환할 사전학습된 모델을 지정합니다.
embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="jhgan/ko-sroberta-multitask"
)

# 컬렉션 가져오기 또는 생성:
# 지정한 이름과 임베딩 함수로 컬렉션이 있으면 가져오고, 없으면 새로 만듭니다.
collection = chroma_client.get_or_create_collection(
    name=collection_name,
    embedding_function=embedding_function
)

# 대화 기록을 저장할 리스트
conversation_history = [
    {"role": "system", "content": "당신은 주문을 받는 사람입니다. 친절하게 고객에게 주문을 받아주세요. 고객은 아주 높은 확률로 한국어를 사용할 것이나, 다른 언어로도 문의할 수 있습니다. 다른 언어로 문의할 경우, 해당 언어로 답변해주세요."}
]

def initialize_vector_store():
    # SQLite 연결
    conn = sqlite3.connect("C://PROJECT//data//cafe_juno.db")
    cursor = conn.cursor()

    # 데이터 조회
    cursor.execute("SELECT A.MENU_ID, A.MENU_NM, B.MENU_SIZE, B.MENU_PRICE FROM MENU_INFO A, MENU_PRICE B WHERE A.MENU_ID = B.MENU_ID")
    rows = cursor.fetchall()

    texts = []
    metadatas = []
    ids = []
    for row in rows:
        menu_id, menu_nm, menu_size, menu_price = row
        # 텍스트: 검색 대상 (임베딩)
        text = f"메뉴:{menu_nm}, 사이즈:{menu_size}, 가격:{menu_price}원"
        texts.append(text)
        # 메타데이터: 추가 정보
        metadatas.append({"id": menu_id, "size": menu_size, "price": menu_price})
        ids.append(str(uuid.uuid4()))

    # 기존 데이터 삭제 (중복 방지)
    collection.delete(ids=ids)

    # 벡터 생성 및 데이터 추가
    embeddings = embedder.encode(texts).tolist()
    collection.add(
        ids=ids,
        embeddings=embeddings,
        metadatas=metadatas,
        documents=texts
    )
    print("데이터 로드 및 임베딩 완료! 데이터 수:", len(rows))
    conn.close()

def retrieve_relevant_context(query, n_results=4):
    query_embedding = embedder.encode([query]).tolist()
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=n_results,
        include=["metadatas", "documents"]
    )
    return results["documents"][0], results["metadatas"][0]


def chat_with_gpt(user_input):
    
    # 관련 문서 검색
    context_texts, context_metadatas = retrieve_relevant_context(user_input)

    # 컨텍스트를 프롬프트에 포함
    context = "\n".join([f"[{meta['id']}]: {text} (가격: {meta['price']}원)" for text, meta in zip(context_texts, context_metadatas)])
    prompt = f"""
        컨텍스트: {context}
        질문: {user_input}
        
        당신은 juno-cafe의 주문을 받는 챗봇입니다. 고객의 주문을 메뉴얼에 따라 단계별로 친절하게 받아주세요.
        1단계 후 2단계 후 3단계 후 4단계 후 5단계 후 6단계로 진행합니다. (고객이 이미 모든 정보를 제공했다면 생략해도 됩니다.)

        나는 한국어가 아닌 다른 언어로도 문의할 수 있습니다.
        한국어로 문의할 경우, 한국어로 답변해주세요. 다른 언어(영어, 일본어 등)로 문의할 경우, 해당 언어로 답변해주세요.

        [주문 메뉴얼]
        1단계 : 메뉴 선택
        2단계 : 아이스 또는 (예 : 아이스로 말씀하시는 건가요?)
        3단계 : 사이즈 선택 (예 : 사이즈 선택 부탁드립니다)
        4단계 : Takeout 여부 선택 (예 : 드시고 가시나요?)
        5단계 : 주문 완료 전 고객 주문 확인 (예 : 주문 확인 부탁드립니다. )
        6단계 : 주문 완료 후 감사 인사 (예 : 감사합니다. 주문이 완료되었습니다.)

        사이즈 관련 정보는 다음과 같습니다:
        - TALL : 톨 (일반 사이즈)
        - GRANDE : 그란데 (조금 큰 사이즈)
        - VENTI : 벤티 (가장 큰 사이즈)

        제공된 컨텍스트 기반으로만 답변해주세요. 
        컨텍스트 기반으로 대답하기 어렵다고 판단되면 '직원 호출이 되었습니다. 잠시만 기다려 주세요.'라고 답변해주세요."
    """
    # 사용자 입력을 대화 기록에 추가
    conversation_history.append({"role": "user", "content": prompt})
    
    # OpenAI API 호출
    response = client.chat.completions.create(
        model="gpt-4.1-mini",  # 또는 사용 가능한 다른 모델 (예: gpt-4o)
        messages=conversation_history,
        max_tokens=150,  # 응답 길이 제한
        temperature=0.7  # 창의성 조절
    )
    
    # GPT 응답 추출
    gpt_response = response.choices[0].message.content.strip()
    
    # 응답을 대화 기록에 추가
    conversation_history.append({"role": "assistant", "content": gpt_response})
    
    return gpt_response

def main():
    initialize_vector_store()
    print("안녕하세요. JUNO-CAFE 입니다. 주문하시겠어요? ))종료하려면 'exit' 입력하세요.((")
    while True:
        user_input = input("You: ")
        if user_input.lower() == "exit":
            print("챗봇을 종료합니다. 감사합니다!")
            break
        if user_input.strip():
            response = chat_with_gpt(user_input)
            print(f"Bot: {response}")

if __name__ == "__main__":
    main()