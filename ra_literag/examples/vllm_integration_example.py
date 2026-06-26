"""
vLLM Integration Example with RAG-Anything

This example demonstrates how to integrate vLLM with RAG-Anything for
high-throughput document processing and querying using locally or remotely
served models.

vLLM provides an OpenAI-compatible API server with continuous batching,
PagedAttention, and optimized inference — ideal for production RAG workloads.

Requirements:
- vLLM serving a model (see: https://docs.vllm.ai/en/latest/serving/openai_compatible_server.html)
- RAG-Anything installed: pip install raganything

Start vLLM (example):
    # Chat / completion model
    vllm serve Qwen/Qwen2.5-72B-Instruct --tensor-parallel-size 4

    # Embedding model (separate process, different port)
    vllm serve BAAI/bge-m3 --task embedding --port 8001

Environment Setup:
Create a .env file with:
LLM_SERVICE_BASE_URL=http://localhost:8081
LLM_SERVICE_LLM_PROVIDER=vllm
LLM_SERVICE_EMBEDDING_PROVIDER=vllm
LLM_MODEL=Qwen/Qwen2.5-72B-Instruct
EMBEDDING_MODEL=BAAI/bge-m3
"""

import os
import uuid
import asyncio
from typing import List, Dict, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# RAG-Anything imports
from raganything import RAGAnything, RAGAnythingConfig
from lightrag.utils import EmbeddingFunc
from examples.doc_processing_helpers import (
    build_doc_processing_llm_client,
    build_doc_processing_embedding_client,
    completion_func,
    embeddings_func,
)

VLLM_MODEL_NAME = os.getenv("LLM_MODEL", "Qwen/Qwen2.5-72B-Instruct")
VLLM_EMBED_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")


async def vllm_llm_model_func(
    prompt: str,
    system_prompt: Optional[str] = None,
    history_messages: List[Dict] = None,
    **kwargs,
) -> str:
    """Top-level LLM function for LightRAG (pickle-safe).

    Uses doc-processing `/llm/complete` as the completion entry point.
    """
    client = build_doc_processing_llm_client()
    return await completion_func(
        client,
        prompt=prompt,
        system_prompt=system_prompt,
        history_messages=history_messages or [],
        model=VLLM_MODEL_NAME,
        **kwargs,
    )


async def vllm_embedding_async(texts: List[str]) -> List[List[float]]:
    """Top-level embedding function via doc-processing."""
    client = build_doc_processing_embedding_client()
    dim = int(os.getenv("EMBEDDING_DIM", "1024"))
    embeddings = await embeddings_func(
        client,
        texts=texts,
        model=VLLM_EMBED_MODEL,
        dimensions=dim,
    )
    return embeddings


class VLLMRAGIntegration:
    """Integration class for vLLM with RAG-Anything."""

    def __init__(self):
        self.model_name = os.getenv("LLM_MODEL", "Qwen/Qwen2.5-72B-Instruct")
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")

        # RAG-Anything configuration
        # Use a fresh working directory each run to avoid legacy doc_status schema conflicts
        self.config = RAGAnythingConfig(
            working_dir=f"./rag_storage_vllm/{uuid.uuid4()}",
            parser="mineru",
            parse_method="auto",
            enable_image_processing=False,
            enable_table_processing=True,
            enable_equation_processing=True,
        )
        print(f"📁 Using working_dir: {self.config.working_dir}")

        self.rag = None

    async def test_connection(self) -> bool:
        """Test doc-processing connection and list configured models."""
        try:
            dp_client = build_doc_processing_llm_client()
            print("🔌 Testing doc-processing connection")
            models = await dp_client.models()
            model_list = models.get("models", [])
            print(f"✅ Connected successfully! Found {len(model_list)} configured models")
            print("📊 Configured models:")
            for i, model in enumerate(model_list[:5]):
                marker = "🎯" if model == self.model_name else "  "
                print(f"{marker} {i+1}. {model}")

            return True
        except Exception as e:
            print(f"❌ Connection failed: {str(e)}")
            print("\n💡 Troubleshooting tips:")
            print("1. Ensure doc-processing service is running")
            print("2. Verify LLM_SERVICE_BASE_URL in your environment")
            print("3. Ensure doc-processing is configured with your vLLM model/provider")
            return False

    async def test_chat_completion(self) -> bool:
        """Test basic chat functionality."""
        try:
            print("💬 Testing completion via doc-processing /llm/complete")
            dp_client = build_doc_processing_llm_client()
            result = await dp_client.complete(
                messages=[
                    {"role": "system", "content": "You are a helpful AI assistant."},
                    {"role": "user", "content": "Confirm the integration is working."},
                ],
                model=self.model_name,
            )
            print("✅ Chat test successful!")
            print(f"Response: {result}")
            return True
        except Exception as e:
            print(f"❌ Chat test failed: {str(e)}")
            return False

    def embedding_func_factory(self):
        """Create a completely serializable embedding function."""
        return EmbeddingFunc(
            embedding_dim=int(os.getenv("EMBEDDING_DIM", "1024")),
            max_token_size=8192,  # bge-m3 context length
            func=vllm_embedding_async,
        )

    async def initialize_rag(self):
        """Initialize RAG-Anything with vLLM functions."""
        print("Initializing RAG-Anything with vLLM...")

        try:
            self.rag = RAGAnything(
                config=self.config,
                llm_model_func=vllm_llm_model_func,
                embedding_func=self.embedding_func_factory(),
            )

            # Compatibility: avoid writing unknown field 'multimodal_processed' to LightRAG doc_status
            async def _noop_mark_multimodal(doc_id: str):
                return None

            self.rag._mark_multimodal_processing_complete = _noop_mark_multimodal

            print("✅ RAG-Anything initialized successfully!")
            return True
        except Exception as e:
            print(f"❌ RAG initialization failed: {str(e)}")
            return False

    async def process_document_example(self, file_path: str):
        """Example: Process a document with vLLM backend."""
        if not self.rag:
            print("❌ RAG not initialized. Call initialize_rag() first.")
            return

        try:
            print(f"📄 Processing document: {file_path}")
            await self.rag.process_document_complete(
                file_path=file_path,
                output_dir="./output_vllm",
                parse_method="auto",
                display_stats=True,
            )
            print("✅ Document processing completed!")
        except Exception as e:
            print(f"❌ Document processing failed: {str(e)}")

    async def query_examples(self):
        """Example queries with different modes."""
        if not self.rag:
            print("❌ RAG not initialized. Call initialize_rag() first.")
            return

        # Example queries
        queries = [
            ("What are the main topics in the processed documents?", "hybrid"),
            ("Summarize any tables or data found in the documents", "local"),
            ("What images or figures are mentioned?", "global"),
        ]

        print("\n🔍 Running example queries...")
        for query, mode in queries:
            try:
                print(f"\nQuery ({mode}): {query}")
                result = await self.rag.aquery(query, mode=mode)
                print(f"Answer: {result[:200]}...")
            except Exception as e:
                print(f"❌ Query failed: {str(e)}")

    async def simple_query_example(self):
        """Example basic text query with sample content."""
        if not self.rag:
            print("❌ RAG not initialized")
            return

        try:
            print("\nAdding sample content for testing...")

            # Create content list in the format expected by RAGAnything
            content_list = [
                {
                    "type": "text",
                    "text": """vLLM Integration with RAG-Anything

This integration demonstrates how to connect vLLM's high-performance inference engine
with RAG-Anything's multimodal document processing capabilities. The system uses:

- vLLM for high-throughput LLM inference with continuous batching
- PagedAttention for efficient memory management
- Tensor parallelism for serving large models across multiple GPUs
- RAG-Anything for document processing and retrieval

Key benefits include:
- Production throughput: Continuous batching serves many concurrent requests
- Memory efficiency: PagedAttention reduces GPU memory waste by up to 90%
- Scalability: Tensor parallelism distributes large models across GPUs
- OpenAI compatibility: Drop-in replacement for OpenAI API clients
- Quantization support: AWQ, GPTQ, and FP8 for reduced memory footprint""",
                    "page_idx": 0,
                }
            ]

            # Insert the content list using the correct method
            await self.rag.insert_content_list(
                content_list=content_list,
                file_path="vllm_integration_demo.txt",
                doc_id=f"demo-content-{uuid.uuid4()}",
                display_stats=True,
            )
            print("✅ Sample content added to knowledge base")

            print("\nTesting basic text query...")

            # Simple text query example
            result = await self.rag.aquery(
                "What are the key benefits of using vLLM for RAG workloads?",
                mode="hybrid",
            )
            print(f"✅ Query result: {result[:300]}...")

        except Exception as e:
            print(f"❌ Query failed: {str(e)}")


async def main():
    """Main example function."""
    print("=" * 70)
    print("vLLM + RAG-Anything Integration Example")
    print("=" * 70)

    # Initialize integration
    integration = VLLMRAGIntegration()

    # Test connection
    if not await integration.test_connection():
        return False

    print()
    if not await integration.test_chat_completion():
        return False

    # Initialize RAG
    print("\n" + "─" * 50)
    if not await integration.initialize_rag():
        return False

    # Example document processing (uncomment and provide a real file path)
    # await integration.process_document_example("path/to/your/document.pdf")

    # Example queries (uncomment after processing documents)
    # await integration.query_examples()

    # Example basic query
    await integration.simple_query_example()

    print("\n" + "=" * 70)
    print("Integration example completed successfully!")
    print("=" * 70)

    return True


if __name__ == "__main__":
    print("🚀 Starting vLLM integration example...")
    success = asyncio.run(main())

    exit(0 if success else 1)
