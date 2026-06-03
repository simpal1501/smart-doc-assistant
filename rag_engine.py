import os
from typing import List, Dict, Any, Tuple
try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
import google.generativeai as genai

# Setup directories for local database persistence
DB_DIR = os.path.join(os.path.dirname(__file__), "chroma_db")

class RAGEngine:
    def __init__(self):
        # Initialize a lightweight, high-quality embedding model that runs completely locally on CPU
        print("Initializing local Embedding model (all-MiniLM-L6-v2)...")
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        self.vector_store = None
        
    def process_pdf(self, file_path: str) -> int:
        """
        Loads a PDF, splits it into semantic chunks, and stores them in the local Vector Database.
        Returns the number of chunks stored.
        """
        # 1. Load the PDF file
        loader = PyPDFLoader(file_path)
        documents = loader.load()
        
        # 2. Split the text into manageable chunks
        # Chunk size is 1000 characters with 200 overlap to maintain context between split boundaries
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, 
            chunk_overlap=200,
            length_function=len
        )
        chunks = text_splitter.split_documents(documents)
        
        # 3. Store the chunk embeddings in ChromaDB (persistent locally)
        # Using a unique collection name based on the file name or global
        self.vector_store = Chroma.from_documents(
            documents=chunks,
            embedding=self.embeddings,
            persist_directory=DB_DIR
        )
        
        return len(chunks)

    def retrieve_context(self, query: str, k: int = 3) -> List[Tuple[Any, float]]:
        """
        Searches the Vector DB for the top 'k' most relevant document sections.
        """
        if not self.vector_store:
            # Try reloading from disk if it was already created previously
            if os.path.exists(DB_DIR):
                self.vector_store = Chroma(
                    persist_directory=DB_DIR,
                    embedding_function=self.embeddings
                )
            else:
                return []
                
        # Perform similarity search with relevance scores
        results = self.vector_store.similarity_search_with_relevance_scores(query, k=k)
        return results

    def generate_answer(self, query: str, context_docs: List[Any], api_key: str = None) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Generates a natural language answer based ON the retrieved context documents.
        Supports both Gemini API and a rule-based mock engine for offline testing.
        """
        # Format the context snippets and citations
        context_text = ""
        citations = []
        
        for i, doc in enumerate(context_docs):
            page_num = doc.metadata.get("page", 0) + 1  # LangChain pages are 0-indexed
            source = os.path.basename(doc.metadata.get("source", "Document"))
            context_text += f"\n[Source: {source}, Page: {page_num}]\n{doc.page_content}\n"
            
            citations.append({
                "index": i + 1,
                "source": source,
                "page": page_num,
                "text": doc.page_content[:200] + "..."  # Snippet
            })
            
        if not context_text:
            return "No matching context found. Please upload a document first.", []

        # Prompt engineering: Force the LLM to only answer using the retrieved context
        prompt = f"""
You are a highly detailed and helpful Smart Document Assistant.
Your task is to answer the user's question using ONLY the provided context blocks. 
If the answer cannot be found in the context, state that you do not know. 
Do not make up facts or use external knowledge.

---
CONTEXT:
{context_text}
---

USER QUESTION:
{query}

ANSWER:
"""

        # Check if Google Gemini API key is provided
        if api_key:
            try:
                genai.configure(api_key=api_key)
                # Using gemini-2.5-flash for speed and low cost
                model = genai.GenerativeModel('gemini-2.5-flash')
                response = model.generate_content(prompt)
                return response.text, citations
            except Exception as e:
                return f"Error communicating with Gemini API: {str(e)}\n\n(Falling back to local heuristic response below)\n\n" + self._mock_response(query, context_docs), citations
        else:
            # Offline Local Helper Mode (if user doesn't have an API key yet)
            local_response = (
                "⚠️ **Running in Offline/Local Mode (No Gemini API Key)**\n\n"
                "To get full generative AI responses, please add your Gemini API Key in the sidebar.\n\n"
                "**Relevant segments found in your document:**\n\n"
                + "\n\n".join([f"**From page {c['page']}:**\n_{doc.page_content}_" for c, doc in zip(citations, context_docs)])
            )
            return local_response, citations

    def _mock_response(self, query: str, context_docs: List[Any]) -> str:
        """Fallback local response summarizing found sections."""
        summary = "Based on the matched sections:\n"
        for doc in context_docs:
            page = doc.metadata.get("page", 0) + 1
            summary += f"- [Page {page}]: {doc.page_content[:150]}...\n"
        return summary

    def generate_summary(self, api_key: str = None) -> str:
        """
        Retrieves the top segments of the loaded document and generates a structured summary.
        """
        if not self.vector_store:
            if os.path.exists(DB_DIR):
                self.vector_store = Chroma(
                    persist_directory=DB_DIR,
                    embedding_function=self.embeddings
                )
            else:
                return "No document has been uploaded yet. Please upload a PDF in the sidebar."
                
        try:
            results = self.vector_store.get(limit=5)
            documents = results.get("documents", [])
            metadatas = results.get("metadatas", [])
            
            if not documents:
                return "The document database is empty."
                
            context_text = ""
            for text, meta in zip(documents, metadatas):
                page = meta.get("page", 0) + 1
                context_text += f"\n[Page: {page}]\n{text}\n"
        except Exception as e:
            return f"Error retrieving document text: {str(e)}"
            
        prompt = f"""
You are an expert document analyst. Analyze and generate a highly professional, structured executive summary of the following document.
Focus strictly on the facts present in the text. Do not invent details.

Format your output using clean markdown as follows:
### 📋 Executive Summary
*(Provide a concise 2-3 sentence overview of the document)*

### 🔑 Key Takeaways
*(Bullet points of 3-5 major highlights, statistics, or facts found)*

---
DOCUMENT CONTENT:
{context_text}
"""

        if api_key:
            try:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-2.5-flash')
                response = model.generate_content(prompt)
                return response.text
            except Exception as e:
                return f"Error communicating with Gemini API: {str(e)}"
        else:
            # Offline mock summary fallback
            return (
                "⚠️ **Offline Mode (No API Key)**\n\n"
                "Here are the first few sentences extracted from your document:\n\n"
                + "\n\n".join([f"**Page {meta.get('page', 0)+1}:** {text[:150]}..." for text, meta in zip(documents[:3], metadatas[:3])])
            )

    def generate_quiz(self, api_key: str = None) -> str:
        """
        Retrieves segments of the loaded document and designs an interactive 3-question MCQ quiz.
        """
        if not self.vector_store:
            if os.path.exists(DB_DIR):
                self.vector_store = Chroma(
                    persist_directory=DB_DIR,
                    embedding_function=self.embeddings
                )
            else:
                return "No document has been uploaded yet. Please upload a PDF in the sidebar."
                
        try:
            results = self.vector_store.get(limit=5)
            documents = results.get("documents", [])
            metadatas = results.get("metadatas", [])
            
            if not documents:
                return "The document database is empty."
                
            context_text = ""
            for text, meta in zip(documents, metadatas):
                page = meta.get("page", 0) + 1
                context_text += f"\n[Page: {page}]\n{text}\n"
        except Exception as e:
            return f"Error retrieving document text: {str(e)}"
            
        prompt = f"""
You are an AI instructor. Based on the provided document content, generate a multiple-choice study quiz with exactly 3 questions.
For each question, provide 4 options (A, B, C, D) and specify the correct answer with a brief explanation.

Format your output using clean markdown as follows:
### 📝 Interactive Quiz

**Question 1:** [Question Text]
- A) [Option A]
- B) [Option B]
- C) [Option C]
- D) [Option D]

*Answer:* **[Correct Option, e.g. A]** - [Brief explanation citing context]

*(Repeat for Question 2 and 3)*

---
DOCUMENT CONTENT:
{context_text}
"""

        if api_key:
            try:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-2.5-flash')
                response = model.generate_content(prompt)
                return response.text
            except Exception as e:
                return f"Error communicating with Gemini API: {str(e)}"
        else:
            return (
                "⚠️ **Offline Mode (No API Key)**\n\n"
                "Please add a Gemini API Key in the sidebar to generate custom quizzes based on your document content!"
            )

