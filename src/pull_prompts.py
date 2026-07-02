"""
Script para fazer pull de prompts do LangSmith Prompt Hub.

Este script:
1. Conecta ao LangSmith usando credenciais do .env
2. Faz pull dos prompts do Hub
3. Salva localmente em prompts/bug_to_user_story_v1.yml

SIMPLIFICADO: Usa serialização nativa do LangChain para extrair prompts.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from langchain import hub
from utils import save_yaml, check_env_vars, print_section_header

load_dotenv()


def pull_prompts_from_langsmith():
    """Faz pull do prompt do LangSmith Hub e salva localmente."""
    print_section_header("PULL PROMPTS FROM LANGSMITH")
    
    if not check_env_vars(["LANGSMITH_API_KEY"]):
        return False
        
    prompt_name = "leonanluppi/bug_to_user_story_v1"
    try:
        print(f"Puxando prompt do LangSmith Hub: {prompt_name}")
        prompt = hub.pull(prompt_name)
        print("✓ Prompt carregado com sucesso")
        
        system_prompt = ""
        user_prompt = ""
        
        for message in prompt.messages:
            role = message.__class__.__name__
            if "System" in role:
                if hasattr(message, 'prompt') and hasattr(message.prompt, 'template'):
                    system_prompt = message.prompt.template
                elif hasattr(message, 'content'):
                    system_prompt = message.content
            elif "Human" in role or "User" in role:
                if hasattr(message, 'prompt') and hasattr(message.prompt, 'template'):
                    user_prompt = message.prompt.template
                elif hasattr(message, 'content'):
                    user_prompt = message.content
        
        yaml_data = {
            "bug_to_user_story_v1": {
                "description": "Prompt para converter relatos de bugs em User Stories",
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "version": "v1",
                "created_at": "2025-01-15",
                "tags": ["bug-analysis", "user-story", "product-management"]
            }
        }
        
        output_path = "prompts/bug_to_user_story_v1.yml"
        if save_yaml(yaml_data, output_path):
            print(f"✓ Prompt salvo com sucesso em: {output_path}")
            return True
        else:
            print("❌ Falha ao salvar YAML localmente")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao fazer pull do prompt: {e}")
        return False


def main():
    """Função principal"""
    success = pull_prompts_from_langsmith()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
