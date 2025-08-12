import os
import uuid
import sqlite3
import chromadb
import chromadb.utils.embedding_functions as embedding_functions

from openai import OpenAI
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

# OpenAI API 키 설정 (환경 변수에서 가져오거나 직접 입력)
load_dotenv()

# OpenAI 클라이언트 초기화
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# ChromaDB 클라이언트 초기화: 데이터베이스와 연결할 클라이언트 객체를 생성합니다.
chroma_client = chromadb.Client()

# 한국어 특화 Sentence-Transformers 모델 로드
embedder = SentenceTransformer('jhgan/ko-sroberta-multitask')

# 사용할 컬렉션(데이터 그룹)의 이름을 지정합니다.
collection_name = "juno-cafe"

# 임베딩 함수 정의: 문장을 벡터로 변환할 사전학습된 모델을 지정합니다.
embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="jhgan/ko-sroberta-multitask"
)

collection = chroma_client.get_or_create_collection(
    name=collection_name,
    embedding_function=embedding_function
)

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

    conn.close()

# 대화 기록을 저장할 리스트
conversation_history = []
def clear_conversation_history():
    
    global conversation_history
    conversation_history = [
        {
            "role": "system",
            "content": """
            당신은 juno-cafe(주노 카페)에서 주문을 받는 봇, 이름은 '마크'입니다.
            당신의 역할은 카페에 온 손님을 친절하고 상냥하게 맞이하고, 그들의 주문을 정확하게 받거나 고객에게 필요한 카페, 메뉴 정보를 제공하는 것입니다. 그 이외의 질문에는 "죄송합니다. 전 알바생이라 그건 답해드릴 수가 없어요."라고 단호하게 거절하며 대답하세요.

            손님은 여러가지 언어로 주문할 수 있습니다. 당신은 손님과 동일한 언어로 대답해야 합니다. 손님이 한국어로 주문하면 한국어로, 일본어로 주문하면 일본어로, 영어로 주문하면 영어로 대답하세요. 당신이 주문을 받을 때 확인이 필요한 것은 4가지 입니다. 1. 음료 종류, 2. 사이즈(톨, 그란데, 벤티), 3. 아이스/핫 여부, 4. 추가 옵션 (ex. 시럽, 휘핑크림 등), 5. 테이크아웃 여부. 만약 고객이 주문을 할 떄 이 4가지 중 하나라도 빠뜨린다면, 당신은 그 부분을 물어봐야 합니다. 예를 들면, 고객이 "아메리카노 톨 사이즈 하나요."라고 말하면 당신은 아이스/핫 여부, 추가 옵션, 테이크아웃 여부를 순서대로 물어봐야 합니다. 이렇게 고객의 주문이 완성되면, 추가로 주문할 내용이 있는지 물어보세요. 만약 고객이 추가 주문이 없다고 하면, 주문을 마무리하면 됩니다.

            주문이 완료되면, 고객의 주문내용을 확인하고, 주문이 완료되었다고 알려주세요.

            """
            }
    ]

def classify_query_type(user_input):

    response = client.chat.completions.create(
        model="gpt-5-nano-2025-08-07",  # 또는 사용 가능한 다른 모델 (예: gpt-4o)
        reasoning={"effort": "low"},
        instructions="사용자 입력의 쿼리 타입을 분류하세요: 'order' (주문/메뉴 문의), info (카페 정보), analytical (분석/비교), other (기타). 출력 형식: 타입: [분류]",
        messages=[
            {"role": "user", input: user_input}
        ],
        max_completion_tokens=50,
        temperature=0.3
    )
    output = response.choices[0].message.content.strip()
    query_type = output.split("타입: ")[-1].lower() if "타입: " in output else "other"
    return query_type

def chat_with_gpt(user_input):
    
    # 관련 문서 검색
    context_texts, context_metadatas = retrieve_relevant_context(user_input)

    # 컨텍스트를 프롬프트에 포함
    context = "\n".join([f"[{meta['id']}]: {text} (가격: {meta['price']}원)" for text, meta in zip(context_texts, context_metadatas)])
    prompt = f"""
        컨텍스트: {context}
        질문: {user_input}
    """
    # 사용자 입력을 대화 기록에 추가
    conversation_history.append({"role": "user", "content": prompt})
    
    # OpenAI API 호출
    response = client.chat.completions.create(
        model="gpt-5-nano",  # 또는 사용 가능한 다른 모델 (예: gpt-4o)
        messages=conversation_history,
        max_completion_tokens=150,  # 응답 길이 제한
        temperature=0.5  # 창의성 조절
    )
    
    # GPT 응답 추출
    gpt_response = response.choices[0].message.content.strip()
    
    # 응답을 대화 기록에 추가
    conversation_history.append({"role": "assistant", "content": gpt_response})
    
    return gpt_response

def main():

    print("안녕하세요. JUNO-CAFE 입니다. 어떻게 도와드릴까요?")

    while True:
        # 사용자 질문
        user_input = input("You: ")

        if user_input.lower() == "exit":
            print("챗봇을 종료합니다. 감사합니다!")
            break   

        if user_input.strip():
            response = chat_with_gpt(user_input)
            print(f"Bot: {response}")


if __name__ == "__main__":
    main() 

