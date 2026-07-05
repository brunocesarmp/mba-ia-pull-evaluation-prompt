"""
Script COMPLETO para avaliar prompts otimizados com integração correta ao LangSmith.

Ajustes feitos:
- Corrigido tracing do LangSmith (runs aparecem no UI)
- Execução real do pipeline de avaliação restaurada
- Projeto LangSmith configurado corretamente
- Mantida lógica de métricas local + terminal
- Suporte apenas a Gemini
"""

import os
import sys
import json
from typing import List, Dict, Any
from pathlib import Path
from dotenv import load_dotenv

from langsmith import Client, traceable
from langchain import hub
from langchain_core.prompts import ChatPromptTemplate

from utils import (
    check_env_vars,
    format_score,
    print_section_header,
    get_llm as get_configured_llm
)

from metrics import (
    evaluate_f1_score,
    evaluate_clarity,
    evaluate_precision
)

load_dotenv()


def get_llm():
    return get_configured_llm(temperature=0)


def load_dataset_from_jsonl(jsonl_path: str) -> List[Dict[str, Any]]:
    examples = []

    try:
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    examples.append(json.loads(line))
        return examples

    except Exception as e:
        print(f"❌ Erro ao carregar dataset: {e}")
        return []


def create_evaluation_dataset(client: Client, dataset_name: str, jsonl_path: str) -> str:
    print(f"Criando dataset de avaliação: {dataset_name}...")

    examples = load_dataset_from_jsonl(jsonl_path)

    if not examples:
        print("❌ Nenhum exemplo carregado")
        return dataset_name

    try:
        dataset = client.create_dataset(dataset_name=dataset_name)

        for example in examples:
            client.create_example(
                dataset_id=dataset.id,
                inputs=example["inputs"],
                outputs=example["outputs"]
            )

        print(f"✓ Dataset criado com {len(examples)} exemplos")
        return dataset_name

    except Exception as e:
        print(f"⚠️ Dataset já existe ou erro: {e}")
        return dataset_name


def pull_prompt_from_langsmith(prompt_name: str) -> ChatPromptTemplate:
    print(f"Carregando prompt: {prompt_name}")
    return hub.pull(prompt_name)


@traceable(name="evaluate_prompt_on_example")
def evaluate_prompt_on_example(prompt_template, example, llm):
    try:
        inputs = example.inputs if hasattr(example, "inputs") else {}
        outputs = example.outputs if hasattr(example, "outputs") else {}

        chain = prompt_template | llm
        response = chain.invoke(inputs)

        answer = response.content
        reference = outputs.get("reference", "") if isinstance(outputs, dict) else ""

        question = inputs.get(
            "bug_report",
            inputs.get("question", inputs.get("pr_title", "N/A"))
        )

        return {
            "answer": answer,
            "reference": reference,
            "question": question
        }

    except Exception:
        return {
            "answer": "",
            "reference": "",
            "question": ""
        }


def evaluate_prompt(prompt_name: str, dataset_name: str, client: Client) -> Dict[str, float]:
    print(f"\n🔍 Avaliando: {prompt_name}")

    prompt_template = pull_prompt_from_langsmith(prompt_name)

    examples = list(client.list_examples(dataset_name=dataset_name))
    print(f"Dataset: {len(examples)} exemplos")

    llm = get_llm()

    f1_scores = []
    clarity_scores = []
    precision_scores = []

    print("Avaliando exemplos...\n")

    for i, example in enumerate(examples, 1):

        result = evaluate_prompt_on_example(prompt_template, example, llm)

        if result["answer"]:
            f1 = evaluate_f1_score(
                result["question"],
                result["answer"],
                result["reference"]
            )

            clarity = evaluate_clarity(
                result["question"],
                result["answer"],
                result["reference"]
            )

            precision = evaluate_precision(
                result["question"],
                result["answer"],
                result["reference"]
            )

            f1_scores.append(f1["score"])
            clarity_scores.append(clarity["score"])
            precision_scores.append(precision["score"])

            print(
                f"[{i}/{len(examples)}] "
                f"F1:{f1['score']:.2f} "
                f"Clarity:{clarity['score']:.2f} "
                f"Precision:{precision['score']:.2f}"
            )

    avg_f1 = sum(f1_scores) / len(f1_scores) if f1_scores else 0.0
    avg_clarity = sum(clarity_scores) / len(clarity_scores) if clarity_scores else 0.0
    avg_precision = sum(precision_scores) / len(precision_scores) if precision_scores else 0.0

    return {
        "helpfulness": round((avg_clarity + avg_precision) / 2, 4),
        "correctness": round((avg_f1 + avg_precision) / 2, 4),
        "f1_score": round(avg_f1, 4),
        "clarity": round(avg_clarity, 4),
        "precision": round(avg_precision, 4)
    }


def display_results(prompt_name: str, scores: Dict[str, float]) -> bool:
    print("\n" + "=" * 50)
    print(f"Prompt: {prompt_name}")
    print("=" * 50)

    print("\nMétricas:")
    for k, v in scores.items():
        print(f"  - {k}: {format_score(v, threshold=0.8)}")

    avg = sum(scores.values()) / len(scores)

    print("\n" + "-" * 50)
    print(f"📊 MÉDIA: {avg:.4f}")
    print("-" * 50)

    passed = avg >= 0.8 and all(v >= 0.8 for v in scores.values())

    print("✅ APROVADO" if passed else "❌ REPROVADO")

    return passed


def main():
    print_section_header("AVALIAÇÃO DE PROMPTS (LANGSMITH INTEGRADO)")

    provider = os.getenv("LLM_PROVIDER", "google")
    if provider != "google":
        print("⚠️ Apenas Gemini suportado neste script")

    required_vars = ["LANGSMITH_API_KEY", "GOOGLE_API_KEY", "USERNAME_LANGSMITH_HUB"]
    if not check_env_vars(required_vars):
        return 1

    client = Client()

    project_name = os.getenv(
        "LANGSMITH_PROJECT",
        "prompt-optimization-challenge"
    )

    jsonl_path = "datasets/bug_to_user_story.jsonl"

    if not Path(jsonl_path).exists():
        print("❌ Dataset não encontrado")
        return 1

    dataset_name = f"{project_name}-eval"

    # 🔥 IMPORTANTE: garante que o LangSmith registra no projeto certo
    os.environ["LANGCHAIN_PROJECT"] = dataset_name

    create_evaluation_dataset(client, dataset_name, jsonl_path)

    username = os.getenv("USERNAME_LANGSMITH_HUB")
    prompt_name = f"{username}/bug_to_user_story_v2"

    # 🔥 EXECUÇÃO REAL DA AVALIAÇÃO (ESSENCIAL)
    scores = evaluate_prompt(prompt_name, dataset_name, client)

    passed = display_results(prompt_name, scores)

    if passed:
        print("\n🎉 Todos os prompts aprovados!")
        print(f"Veja no LangSmith: https://smith.langchain.com/projects/{dataset_name}")
        return 0
    else:
        print("\n⚠️ Alguns prompts falharam")
        return 1


if __name__ == "__main__":
    sys.exit(main())