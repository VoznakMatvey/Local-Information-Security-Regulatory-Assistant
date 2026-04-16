import requests
import json
from pathlib import Path
from typing import List, Dict
from config import OLLAMA_HOST, OLLAMA_MODEL, SYSTEM_PROMPT, TEMPERATURE, MAX_TOKENS

class RAGChain:
    """Формирует промпт, вызывает Ollama, парсит ответ."""
    
    def __init__(self):
        self.ollama_url = f"http://{OLLAMA_HOST}/api/generate"
    
    def _build_prompt(self, query: str, context_docs: List) -> str:
        """Собирает промпт с контекстом из найденных чанков."""
        context_text = ""
        for i, doc in enumerate(context_docs):
            content = doc.page_content
            source = doc.metadata.get('source', 'Неизвестный источник')
            filename = doc.metadata.get('filename', Path(source).name if source else 'Неизвестно')
            page = doc.metadata.get('page', '')
            page_str = f", стр. {page}" if page else ""
            chunk_idx = doc.metadata.get('chunk_index', '')
            chunk_str = f", чанк {chunk_idx}" if chunk_idx != '' else ""
            
            context_text += f"\n--- Фрагмент {i+1} (источник: {filename}{page_str}{chunk_str}) ---\n"
            context_text += content + "\n"
        
        prompt = f"""{SYSTEM_PROMPT}

## Контекст из нормативно-правовых актов:
{context_text}

## Вопрос пользователя:
{query}

## Ответ (со ссылками на источники):
"""
        return prompt
    
    def ask(self, query: str, context_docs: List, temperature: float = None) -> Dict:
        prompt = self._build_prompt(query, context_docs)
        temp = temperature if temperature is not None else TEMPERATURE
        
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temp,
                "num_predict": MAX_TOKENS,
                "top_k": 40,
                "top_p": 0.9
            }
        }
        
        try:
            response = requests.post(self.ollama_url, json=payload, timeout=120)
            response.raise_for_status()
            result = response.json()
            return {
                "success": True,
                "answer": result.get("response", ""),
                "model": OLLAMA_MODEL,
                "context_docs": context_docs
            }
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "answer": "Превышено время ожидания ответа от модели. Попробуйте упростить вопрос.",
                "model": OLLAMA_MODEL,
                "context_docs": context_docs
            }
        except Exception as e:
            return {
                "success": False,
                "answer": f"Ошибка при обращении к Ollama: {str(e)}",
                "model": OLLAMA_MODEL,
                "context_docs": context_docs
            }
    
    def check_ollama_health(self) -> bool:
        try:
            resp = requests.get(f"http://{OLLAMA_HOST}/api/tags", timeout=5)
            return resp.status_code == 200
        except:
            return False