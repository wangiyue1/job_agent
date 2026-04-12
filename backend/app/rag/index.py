"""
chroma run --path ./chroma-data
"""
import logging
from pathlib import Path
from typing import List

from langchain_huggingface.embeddings import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

from .loader import PatentTXTLoader
logger = logging.getLogger(__name__)

class PatentVectorIndex:
    """
    统一封装：
    1. embedding model
    2. Chroma vector store
    3. indexing
    4. retrieval
    """
    def __init__(self,
                embedding_model:str = "BAAI/bge-small-zh-v1.5",
                collection_name: str = "patent_records",
                data_path: str | Path = "./data/patents.json",
                persist_directory: str | Path = "data/chroma_patents",
                ) -> None:
        self.embedding_model = embedding_model
        self.collection_name = collection_name
        self.data_path = Path(data_path)
        self.persist_directory = Path(persist_directory)
        
        self.loader = PatentTXTLoader()
        self.embedding = self._build_embedding()
        self.vector_store = self._build_vector_store()
    
    # =========================
    # 基础组件
    # =========================  
    def _build_embedding(self) -> HuggingFaceEmbeddings:
        return HuggingFaceEmbeddings(
            model_name=self.embedding_model,
            model_kwargs = {"device": "cpu"},
            encode_kwargs = {"normalize_embeddings": True},
        )
    
    def _build_vector_store(self) -> Chroma:
        return Chroma(
            collection_name=self.collection_name,
            embedding_function=self.embedding,
            persist_directory=self.persist_directory,
        )
    
    # =========================
    # 建库 / 入库
    # =========================
    def add_docuemnts(self, documents: List[Document]) -> None:
        """将文档添加到向量库中"""
        if not documents:
            logger.warning("No documents to add.")
            return
        self.vector_store.add_documents(documents)
        logger.info(f"Added {len(documents)} documents to the vector store.")
        
    def build_documents_from_json(self, reset_collection: bool = False) -> int:
        if reset_collection:
            self.reset_collection()
        docs = self.loader.load_documents_from_json_file(self.data_path)
        self.add_docuemnts(docs)
        return len(docs)

    def reset_collection(self) -> None:
        """重置向量库，删除所有数据"""
        try:
            self.vector_store.delete_collection()
            logger.info(f"Collection '{self.collection_name}' has been reset.")
        except Exception as e:
            logger.error(f"Failed to reset collection '{self.collection_name}': {e}")
        self.vector_store = self._build_vector_store()
        
    # =========================
    # 检索
    # =========================
    def similarity_search(self, query: str, top_k: int = 5) -> List[Document]:
        return self.vector_store.similarity_search(query, k=top_k)
    
    def similarity_search_with_score(self, query: str, top_k: int = 5) -> List[tuple[Document, float]]:
        return self.vector_store.similarity_search_with_score(query, k=top_k)
    
    def as_retriever(self, k: int = 5):
        return self.vector_store.as_retriever(search_kwargs={"k": k})

if __name__ == "__main__":
    index = PatentVectorIndex()
    num_docs = index.build_documents_from_json(reset_collection=False)
    print(f"Indexed {num_docs} documents.")
    
    query = "微调的端到端自动驾驶"
    results = index.similarity_search_with_score(query, top_k=3)
    for doc, score in results:
        print(f"Score: {score:.4f}, Document: {doc.page_content[:100]}...")