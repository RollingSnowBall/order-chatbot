import os
import uuid
import sqlite3

from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
import chromadb
import chromadb.utils.embedding_functions as embedding_functions
from openai import OpenAI

# Disable ChromaDB telemetry
os.environ["CHROMA_TELEMETRY"] = "false"

# Load environment variables
load_dotenv()

class CafeBot:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.embedder = SentenceTransformer('jhgan/ko-sroberta-multitask')
        self.chroma_client = chromadb.Client()
        self.collection_name = "juno-cafe"
        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="jhgan/ko-sroberta-multitask"
        )
        self.collection = self.chroma_client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=self.embedding_function
        )
        self.conversation_history = []
        self.clear_conversation_history()

    def clear_conversation_history(self):
        self.conversation_history = [
            {
                "role": "system",
                "content": (
                    """
                    당신은 juno-cafe(주노 카페)에서 주문을 받는 봇, 이름은 '마크'입니다.
                    당신의 역할은 카페에 온 손님을 친절하고 상냥하게 맞이하고, 그들의 주문을 정확하게 받거나 고객에게 필요한 카페, 메뉴 정보를 제공하는 것입니다. 그 이외의 질문에는 "죄송합니다. 전 알바생이라 그건 답해드릴 수가 없어요."라고 대답하세요.

                    손님은 여러가지 언어로 주문할 수 있습니다. 당신은 손님과 동일한 언어로 대답해야 합니다. 손님이 한국어로 주문하면 한국어로, 일본어로 주문하면 일본어로, 영어로 주문하면 영어로 대답하세요. 당신이 주문을 받을 때 확인이 필요한 것은 4가지 입니다. 1. 음료 종류, 2. 사이즈(톨, 그란데, 벤티), 3. 아이스/핫 여부, 4. 추가 옵션 (ex. 시럽, 휘핑크림 등), 5. 테이크아웃 여부. 만약 고객이 주문을 할 떄 이 4가지 중 하나라도 빠뜨린다면, 당신은 그 부분을 물어봐야 합니다. 예를 들면, 고객이 "아메리카노 톨 사이즈 하나요."라고 말하면 당신은 아이스/핫 여부, 추가 옵션, 테이크아웃 여부를 순서대로 물어봐야 합니다. (절대 한번에 모든 것을 요구하지 마세요.) 이렇게 고객의 주문이 완성되면, 추가로 주문할 내용이 있는지 물어보세요. 만약 고객이 추가 주문이 없다고 하면, 주문을 마무리하면 됩니다. 고객이 메뉴를 결정한 것이 아니라면 앞서 언급한 4가지 사항을 아직 언급하지 마세요. (고객이 당신에게 질문을 했다면 그것은 메뉴를 아직 결정하지 않았다는 의미입니다.) 고객이 메뉴를 결정한 후에야 4가지 (사이즈, 아이스/핫 여부, 추가 옵션, 테이크아웃 여부)를 물어보세요. 그리고 최종 주문이 완료된게 아니라면 앞선 4가지 선택사항을 매번 언급하지 마세요.

                    주문이 완료되면, 고객의 주문내용을 확인하고, 주문이 완료되었다고 알려주세요. 추가로 고객의 대화 중에 컨텍스트가 포함되어 있는 경우가 있습니다. 이 경우에는 고객이 한 질문과 유사한 메뉴가 있는 경우를 의미합니다. 컨텍스트에서 제공된 메뉴로만 대답해주세요. 메뉴가 없다면 "오류 메뉴 없음"라고 말하세요.
                    """
                )
            }
        ]

    def initialize_vector_store(self, db_path="C://PROJECT//data//cafe_juno.db"):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT A.MENU_ID, A.MENU_NM, B.MENU_SIZE, B.MENU_PRICE "
            "FROM MENU_INFO A, MENU_PRICE B WHERE A.MENU_ID = B.MENU_ID"
        )
        rows = cursor.fetchall()
        texts, metadatas, ids = [], [], []
        for menu_id, menu_nm, menu_size, menu_price in rows:
            text = f"메뉴:{menu_nm}, 사이즈:{menu_size}, 가격:{menu_price}원"
            texts.append(text)
            metadatas.append({"id": menu_id, "size": menu_size, "price": menu_price})
            ids.append(str(uuid.uuid4()))
        # Remove existing vectors with same ids (if any)
        self.collection.delete(ids=ids)
        embeddings = self.embedder.encode(texts).tolist()
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=texts
        )
        conn.close()

    def retrieve_relevant_context(self, query, n_results=10):
        query_embedding = self.embedder.encode([query]).tolist()
        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=n_results,
            include=["metadatas", "documents", "distances"]
        )

        filtered_docs = []
        filtered_metas = []

        for doc, meta, dist in zip(results["documents"][0], results["metadatas"][0], results["distances"][0]):
            if dist < 150:  # 임계값: 유사도 거리가 threshold 미만인 경우만 포함 (튜닝 필요)
                ##print(f"유사도 거리: {dist}, 문서: {doc}")
                filtered_docs.append(doc)
                filtered_metas.append(meta)
            ##else:
                ##print(f"유사도 거리: {dist}는 임계값을 초과하여 제외됨, 문서: {doc}")
        return filtered_docs, filtered_metas

    def chat_with_gpt(self, user_input):
        context_texts, context_metadatas = self.retrieve_relevant_context(user_input)
        context = "\n".join(
            [f"[{meta['id']}]: {text} (가격: {meta['price']}원)"
             for text, meta in zip(context_texts, context_metadatas)]
        )
        prompt = f"컨텍스트: {context}\n질문: {user_input}"
        self.conversation_history.append({"role": "user", "content": prompt})
        response = self.client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=self.conversation_history,
            max_tokens=150,
            temperature=0.7
        )
        gpt_response = response.choices[0].message.content.strip()
        self.conversation_history.append({"role": "assistant", "content": gpt_response})
        return gpt_response

def main():
    bot = CafeBot()
    bot.initialize_vector_store()
    print("안녕하세요. JUNO-CAFE 입니다. 주문하시겠어요? ))종료하려면 'exit' 입력하세요.((")
    while True:
        user_input = input("You: ")
        if user_input.lower() == "exit":
            print("챗봇을 종료합니다. 감사합니다!")
            break
        if user_input.strip():
            response = bot.chat_with_gpt(user_input)
            print(f"Bot: {response}")

if __name__ == "__main__":
    main()
