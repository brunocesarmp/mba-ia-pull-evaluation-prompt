"""
Testes automatizados para validação de prompts.
"""
import pytest
import yaml
import sys
import re
from pathlib import Path

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils import validate_prompt_structure

def load_prompts(file_path: str):
    """Carrega prompts do arquivo YAML."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

class TestPrompts:
    @pytest.fixture(autouse=True)
    def setup_prompt(self):
        file_path = Path(__file__).parent.parent / "prompts" / "bug_to_user_story_v2.yml"
        self.prompts = load_prompts(str(file_path))
        self.prompt_data = self.prompts.get("bug_to_user_story_v2", {})

    def test_prompt_has_system_prompt(self):
        """Verifica se o campo 'system_prompt' existe e não está vazio."""
        assert "system_prompt" in self.prompt_data, "system_prompt não está presente no yaml"
        assert self.prompt_data["system_prompt"].strip(), "system_prompt está vazio"

    def test_prompt_has_role_definition(self):
        """Verifica se o prompt define uma persona (ex: "Você é um Product Manager")."""
        system_prompt = self.prompt_data.get("system_prompt", "").lower()
        role_keywords = ["product manager", "product owner", "gerente de produto", "dono do produto", "pm", "po", "analista de negócios"]
        has_role = any(kw in system_prompt for kw in role_keywords)
        assert has_role, f"Nenhuma definição de persona encontrada no system_prompt. Esperado um dos: {role_keywords}"

    def test_prompt_mentions_format(self):
        """Verifica se o prompt exige formato Markdown ou User Story padrão."""
        system_prompt = self.prompt_data.get("system_prompt", "").lower()
        format_keywords = ["markdown", "user story", "como um", "eu quero", "para que", "given-when-then", "dado", "quando", "então"]
        has_format = any(kw in system_prompt for kw in format_keywords)
        assert has_format, "O prompt não parece exigir formato Markdown ou padrão de User Story (ex: Como um, Eu quero, Para que)."

    def test_prompt_has_few_shot_examples(self):
        """Verifica se o prompt contém exemplos de entrada/saída (técnica Few-shot)."""
        system_prompt = self.prompt_data.get("system_prompt", "").lower()
        few_shot_keywords = ["exemplo", "example", "few-shot", "entrada", "saída", "cenário", "scenario"]
        has_few_shot = any(kw in system_prompt for kw in few_shot_keywords)
        # Além de palavras-chave, vamos verificar se há múltiplos blocos de exemplos ou estrutura típica
        assert has_few_shot, "O prompt não parece conter exemplos de poucas jogadas (few-shot examples)."

    def test_prompt_no_todos(self):
        """Garante que você não esqueceu nenhum `[TODO]` no texto."""
        system_prompt = self.prompt_data.get("system_prompt", "")
        user_prompt = self.prompt_data.get("user_prompt", "")
        description = self.prompt_data.get("description", "")
        
        # Check for case-insensitive TODO as a standalone word or in brackets
        todo_pattern = re.compile(r"\bTODO\b|\[TODO\]", re.IGNORECASE)
        
        assert not todo_pattern.search(system_prompt), "Encontrado TODO no system_prompt"
        assert not todo_pattern.search(user_prompt), "Encontrado TODO no user_prompt"
        assert not todo_pattern.search(description), "Encontrado TODO na descrição"

    def test_minimum_techniques(self):
        """Verifica (através dos metadados do yaml) se pelo menos 2 técnicas foram listadas."""
        techniques = self.prompt_data.get("techniques_applied", [])
        assert isinstance(techniques, list), "techniques_applied deve ser uma lista"
        assert len(techniques) >= 2, f"Pelo menos 2 técnicas devem ser listadas, encontradas {len(techniques)}"

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])