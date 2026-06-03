import os
import re
import json
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
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, 
            chunk_overlap=200,
            length_function=len
        )
        chunks = text_splitter.split_documents(documents)
        
        # 3. Store the chunk embeddings in ChromaDB (persistent locally)
        self.vector_store = Chroma.from_documents(
            documents=chunks,
            embedding=self.embeddings,
            persist_directory=DB_DIR
        )
        
        return len(chunks)

    def get_indexed_files(self) -> List[str]:
        """
        Queries ChromaDB metadata and retrieves a unique list of base file names indexed in the local database.
        """
        if not self.vector_store:
            if os.path.exists(DB_DIR):
                self.vector_store = Chroma(
                    persist_directory=DB_DIR,
                    embedding_function=self.embeddings
                )
            else:
                return []
                
        try:
            results = self.vector_store.get()
            metadatas = results.get("metadatas", [])
            sources = set()
            for meta in metadatas:
                if meta and "source" in meta:
                    sources.add(os.path.basename(meta["source"]))
            return list(sources)
        except Exception:
            return []

    def retrieve_context(self, query: str, k: int = 3, selected_sources: List[str] = None) -> List[Tuple[Any, float]]:
        """
        Searches the Vector DB for the top 'k' most relevant document sections, optionally filtered by source names.
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
                
        # Perform similarity search with relevance scores. Retrieve more if filtering is applied.
        search_k = k * 4 if selected_sources is not None else k
        results = self.vector_store.similarity_search_with_relevance_scores(query, k=search_k)
        
        if selected_sources is not None:
            filtered_results = []
            for doc, score in results:
                source_name = os.path.basename(doc.metadata.get("source", ""))
                if source_name in selected_sources:
                    filtered_results.append((doc, score))
            return filtered_results[:k]
            
        return results[:k]

    def generate_answer(self, query: str, context_docs: List[Any], api_key: str = None, model_name: str = "gemini-2.5-flash") -> Tuple[str, List[Dict[str, Any]]]:
        """
        Generates a natural language answer based ON the retrieved context documents using the selected model.
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
            return "No matching context found. Please select your active documents or upload a document first.", []

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
                model = genai.GenerativeModel(model_name)
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
                + "\n\n".join([f"**From page {c['page']} ({c['source']}):**\n_{doc.page_content}_" for c, doc in zip(citations, context_docs)])
            )
            return local_response, citations

    def _mock_response(self, query: str, context_docs: List[Any]) -> str:
        """Fallback local response summarizing found sections."""
        summary = "Based on the matched sections:\n"
        for doc in context_docs:
            page = doc.metadata.get("page", 0) + 1
            source = os.path.basename(doc.metadata.get("source", "Document"))
            summary += f"- [Page {page} of {source}]: {doc.page_content[:150]}...\n"
        return summary

    def generate_summary(self, api_key: str = None, model_name: str = "gemini-2.5-flash") -> str:
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
                source = os.path.basename(meta.get("source", "Document"))
                context_text += f"\n[File: {source}, Page: {page}]\n{text}\n"
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
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt)
                return response.text
            except Exception as e:
                return f"Error communicating with Gemini API: {str(e)}"
        else:
            # Offline mock summary fallback
            return (
                "⚠️ **Offline Mode (No API Key)**\n\n"
                "Here are the first few sentences extracted from your document:\n\n"
                + "\n\n".join([f"**File {meta.get('source', 'Doc')}, Page {meta.get('page', 0)+1}:** {text[:150]}..." for text, meta in zip(documents[:3], metadatas[:3])])
            )

    def generate_quiz(self, api_key: str = None, model_name: str = "gemini-2.5-flash") -> str:
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
                source = os.path.basename(meta.get("source", "Document"))
                context_text += f"\n[File: {source}, Page: {page}]\n{text}\n"
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
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt)
                return response.text
            except Exception as e:
                return f"Error communicating with Gemini API: {str(e)}"
        else:
            return (
                "⚠️ **Offline Mode (No API Key)**\n\n"
                "Please add a Gemini API Key in the sidebar to generate custom quizzes based on your document content!"
            )

    def generate_flashcards(self, api_key: str = None, model_name: str = "gemini-2.5-flash") -> List[Dict[str, str]]:
        """
        Retrieves document content and generates 5 key concept study flashcards as a list of dicts.
        """
        if not self.vector_store:
            if os.path.exists(DB_DIR):
                self.vector_store = Chroma(
                    persist_directory=DB_DIR,
                    embedding_function=self.embeddings
                )
            else:
                return []
                
        try:
            results = self.vector_store.get(limit=5)
            documents = results.get("documents", [])
            metadatas = results.get("metadatas", [])
            
            if not documents:
                return []
                
            context_text = ""
            for text, meta in zip(documents, metadatas):
                page = meta.get("page", 0) + 1
                source = os.path.basename(meta.get("source", "Document"))
                context_text += f"\n[File: {source}, Page: {page}]\n{text}\n"
        except Exception:
            return []
            
        prompt = f"""
You are an expert educator. Analyze the provided document content and extract exactly 5 key concept study flashcards.
For each flashcard, define a key term, question, or formula as the "front", and its concise definition, explanation, or answer as the "back".

Your response MUST be a valid JSON array of objects. Do not include markdown code block formatting (like ```json). Just return the raw JSON text.
Each object in the array must have exactly these keys:
- "front": A short string representing the front of the flashcard.
- "back": A string representing the back of the flashcard.

---
DOCUMENT CONTENT:
{context_text}
"""
        if api_key:
            try:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt)
                
                # Parse JSON safely
                text = response.text.strip()
                if text.startswith("```"):
                    match = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL | re.IGNORECASE)
                    if match:
                        text = match.group(1).strip()
                
                return json.loads(text)[:5]
            except Exception as e:
                print(f"Error generating flashcards: {{str(e)}}")
                return self._fallback_flashcards(documents, metadatas)
        else:
            return self._fallback_flashcards(documents, metadatas)

    def _fallback_flashcards(self, documents: List[str], metadatas: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        flashcards = []
        for i, (text, meta) in enumerate(zip(documents[:5], metadatas[:5])):
            source = os.path.basename(meta.get("source", "Document"))
            page = meta.get("page", 0) + 1
            flashcards.append({
                "front": f"Key Concept from {source} (Page {page})",
                "back": text[:180] + "..."
            })
        return flashcards

    def extract_glossary(self, api_key: str = None, model_name: str = "gemini-2.5-flash") -> List[Dict[str, str]]:
        """
        Retrieves document content and extracts a glossary of the 6 most important terms and definitions.
        """
        if not self.vector_store:
            if os.path.exists(DB_DIR):
                self.vector_store = Chroma(
                    persist_directory=DB_DIR,
                    embedding_function=self.embeddings
                )
            else:
                return []
                
        try:
            results = self.vector_store.get(limit=6)
            documents = results.get("documents", [])
            metadatas = results.get("metadatas", [])
            
            if not documents:
                return []
                
            context_text = ""
            for text, meta in zip(documents, metadatas):
                page = meta.get("page", 0) + 1
                source = os.path.basename(meta.get("source", "Document"))
                context_text += f"\n[File: {source}, Page: {page}]\n{text}\n"
        except Exception:
            return []
            
        prompt = f"""
You are an expert document indexer. Extract a glossary of the 6 most important terms, acronyms, or concepts from the provided document.
For each term, provide its name and a concise definition based on the document.

Your response MUST be a valid JSON array of objects. Do not include markdown code block formatting (like ```json). Just return the raw JSON text.
Each object in the array must have exactly these keys:
- "term": The name of the term.
- "definition": A brief definition.

---
DOCUMENT CONTENT:
{context_text}
"""
        if api_key:
            try:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt)
                
                # Parse JSON safely
                text = response.text.strip()
                if text.startswith("```"):
                    match = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL | re.IGNORECASE)
                    if match:
                        text = match.group(1).strip()
                
                return json.loads(text)[:6]
            except Exception as e:
                print(f"Error generating glossary: {{str(e)}}")
                return self._fallback_glossary(documents, metadatas)
        else:
            return self._fallback_glossary(documents, metadatas)

    def _fallback_glossary(self, documents: List[str], metadatas: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        glossary = []
        for i, (text, meta) in enumerate(zip(documents[:6], metadatas[:6])):
            # Simple keyword extraction mock
            words = [w for w in text.split() if len(w) > 5 and w.istitle()]
            term = words[0] if words else f"Term {i+1}"
            glossary.append({
                "term": term,
                "definition": text[:150] + "..."
            })
        return glossary
