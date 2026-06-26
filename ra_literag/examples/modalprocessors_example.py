"""
Example of directly using modal processors

This example demonstrates how to use RAG-Anything's modal processors directly without going through MinerU.
"""

import asyncio
import argparse
import os
from lightrag.utils import EmbeddingFunc
from lightrag.kg.shared_storage import initialize_pipeline_status
from lightrag import LightRAG
from raganything.modalprocessors import (
    ImageModalProcessor,
    TableModalProcessor,
    EquationModalProcessor,
)
from examples.doc_processing_helpers import (
    build_doc_processing_llm_client,
    build_doc_processing_embedding_client,
    completion_func,
    vision_completion_func,
    embeddings_func,
)

DEFAULT_WORKING_DIR = "./rag_storage"


def get_llm_model_func():
    client = build_doc_processing_llm_client()

    async def _llm(prompt, system_prompt=None, history_messages=[], **kwargs):
        return await completion_func(
            client,
            prompt=prompt,
            system_prompt=system_prompt,
            history_messages=history_messages,
            **kwargs,
        )

    return _llm


def get_vision_model_func():
    client = build_doc_processing_llm_client()

    async def _vision(
        prompt, system_prompt=None, history_messages=[], image_data=None, **kwargs
    ):
        return await vision_completion_func(
            client,
            prompt=prompt,
            system_prompt=system_prompt,
            history_messages=history_messages,
            image_data=image_data,
            **kwargs,
        )

    return _vision


async def process_image_example(lightrag: LightRAG, vision_model_func):
    """Example of processing an image"""
    # Create image processor
    image_processor = ImageModalProcessor(
        lightrag=lightrag, modal_caption_func=vision_model_func
    )

    # Prepare image content
    image_content = {
        "img_path": "image.jpg",
        "image_caption": ["Example image caption"],
        "image_footnote": ["Example image footnote"],
    }

    # Process image
    (description, entity_info, _) = await image_processor.process_multimodal_content(
        modal_content=image_content,
        content_type="image",
        file_path="image_example.jpg",
        entity_name="Example Image",
    )

    print("Image Processing Results:")
    print(f"Description: {description}")
    print(f"Entity Info: {entity_info}")


async def process_table_example(lightrag: LightRAG, llm_model_func):
    """Example of processing a table"""
    # Create table processor
    table_processor = TableModalProcessor(
        lightrag=lightrag, modal_caption_func=llm_model_func
    )

    # Prepare table content
    table_content = {
        "table_body": """
        | Name | Age | Occupation |
        |------|-----|------------|
        | John | 25  | Engineer   |
        | Mary | 30  | Designer   |
        """,
        "table_caption": ["Employee Information Table"],
        "table_footnote": ["Data updated as of 2024"],
    }

    # Process table
    (description, entity_info, _) = await table_processor.process_multimodal_content(
        modal_content=table_content,
        content_type="table",
        file_path="table_example.md",
        entity_name="Employee Table",
    )

    print("\nTable Processing Results:")
    print(f"Description: {description}")
    print(f"Entity Info: {entity_info}")


async def process_equation_example(lightrag: LightRAG, llm_model_func):
    """Example of processing a mathematical equation"""
    # Create equation processor
    equation_processor = EquationModalProcessor(
        lightrag=lightrag, modal_caption_func=llm_model_func
    )

    # Prepare equation content
    equation_content = {"text": "E = mc^2", "text_format": "LaTeX"}

    # Process equation
    (description, entity_info, _) = await equation_processor.process_multimodal_content(
        modal_content=equation_content,
        content_type="equation",
        file_path="equation_example.txt",
        entity_name="Mass-Energy Equivalence",
    )

    print("\nEquation Processing Results:")
    print(f"Description: {description}")
    print(f"Entity Info: {entity_info}")


async def initialize_rag(working_dir: str):
    embedding_dim = int(os.getenv("EMBEDDING_DIM", "3072"))
    embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")
    embed_client = build_doc_processing_embedding_client()

    rag = LightRAG(
        working_dir=working_dir,
        embedding_func=EmbeddingFunc(
            embedding_dim=embedding_dim,
            max_token_size=8192,
            func=lambda texts: embeddings_func(
                embed_client,
                texts=texts,
                model=embedding_model,
                dimensions=embedding_dim,
            ),
        ),
        llm_model_func=get_llm_model_func(),
    )

    await rag.initialize_storages()
    await initialize_pipeline_status()

    return rag


def main():
    """Main function to run the example"""
    parser = argparse.ArgumentParser(description="Modal Processors Example")
    parser.add_argument(
        "--working-dir", "-w", default=DEFAULT_WORKING_DIR, help="Working directory path"
    )

    args = parser.parse_args()

    asyncio.run(main_async(args.working_dir))


async def main_async(working_dir: str):
    if not os.getenv("LLM_SERVICE_BASE_URL"):
        raise ValueError("LLM_SERVICE_BASE_URL is required")
    lightrag = await initialize_rag(working_dir)

    # Get model functions
    llm_model_func = get_llm_model_func()
    vision_model_func = get_vision_model_func()

    # Run examples
    await process_image_example(lightrag, vision_model_func)
    await process_table_example(lightrag, llm_model_func)
    await process_equation_example(lightrag, llm_model_func)


if __name__ == "__main__":
    main()
