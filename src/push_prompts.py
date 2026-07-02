"""
Script para fazer push de prompts otimizados ao LangSmith Prompt Hub.

Este script:
1. Lê os prompts otimizados de prompts/bug_to_user_story_v2.yml
2. Valida os prompts
3. Faz push PÚBLICO para o LangSmith Hub
4. Adiciona metadados (tags, descrição, técnicas utilizadas)

SIMPLIFICADO: Código mais limpo e direto ao ponto.
"""

import os
import sys
from dotenv import load_dotenv
from langchain import hub
from langchain_core.prompts import ChatPromptTemplate
from utils import load_yaml, check_env_vars, print_section_header, validate_prompt_structure

load_dotenv()


def push_prompt_to_langsmith(prompt_name: str, prompt_data: dict) -> bool:
    """
    Faz push do prompt otimizado para o LangSmith Hub (PÚBLICO).

    Args:
        prompt_name: Nome do prompt
        prompt_data: Dados do prompt

    Returns:
        True se sucesso, False caso contrário
    """
    try:
        system_prompt = prompt_data.get("system_prompt", "")
        user_prompt = prompt_data.get("user_prompt", "")
        description = prompt_data.get("description", "")
        
        # Construir o ChatPromptTemplate
        chat_prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", user_prompt)
        ])
        
        print(f"Fazendo push do prompt '{prompt_name}'...")
        hub.push(
            prompt_name,
            chat_prompt,
            new_repo_is_public=True,
            new_repo_description=description
        )
        print(f"✓ Push realizado com sucesso!")
        return True
    except Exception as e:
        print(f"❌ Erro ao fazer push para o LangSmith Hub: {e}")
        return False


def validate_prompt(prompt_data: dict) -> tuple[bool, list]:
    """
    Valida estrutura básica de um prompt (versão simplificada).

    Args:
        prompt_data: Dados do prompt

    Returns:
        (is_valid, errors) - Tupla com status e lista de erros
    """
    return validate_prompt_structure(prompt_data)


def main():
    """Função principal"""
    print_section_header("PUSH PROMPTS TO LANGSMITH")
    
    required_vars = ["LANGSMITH_API_KEY", "USERNAME_LANGSMITH_HUB"]
    if not check_env_vars(required_vars):
        return 1
        
    username = os.getenv("USERNAME_LANGSMITH_HUB")
    prompt_file = "prompts/bug_to_user_story_v2.yml"
    
    prompt_dict = load_yaml(prompt_file)
    if not prompt_dict:
        print(f"❌ Falha ao carregar {prompt_file}")
        return 1
        
    # O arquivo v2.yml deve conter a chave 'bug_to_user_story_v2'
    prompt_key = "bug_to_user_story_v2"
    if prompt_key not in prompt_dict:
        print(f"❌ Chave '{prompt_key}' não encontrada no arquivo YAML.")
        return 1
        
    prompt_data = prompt_dict[prompt_key]
    
    # Validar estrutura antes do push
    is_valid, errors = validate_prompt(prompt_data)
    if not is_valid:
        print("❌ Erros de validação no prompt:")
        for err in errors:
            print(f"  - {err}")
        return 1
        
    print("✓ Prompt validado com sucesso!")
    
    target_prompt_name = f"{username}/bug_to_user_story_v2"
    success = push_prompt_to_langsmith(target_prompt_name, prompt_data)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
