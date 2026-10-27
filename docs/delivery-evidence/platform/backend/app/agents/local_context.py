"""Measure the already-loaded model; never load another model as a side effect."""
from urllib.parse import urlparse
import lmstudio


async def measure_context(base_url, model_name, messages):
    address = urlparse(base_url)
    async with lmstudio.AsyncClient(address.netloc) as client:
        models = await client.llm.list_loaded()
        model = next((item for item in models if item.identifier == model_name), None)
        if model is None:
            raise RuntimeError(f'Load {model_name} in LM Studio before starting the project.')
        formatted = await model.apply_prompt_template({'messages': messages})
        return await model.count_tokens(formatted), await model.get_context_length()
