import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from omegaconf import OmegaConf
from pydantic import BaseModel

from data2mcp_v2.server.router import Router
from data2mcp_v2.server.data_summary import build_data_summary
from data2mcp_v2.server.strategy_catalog import load_strategies
from data2mcp_v2.server.strategy_extractor import (
    DEFAULT_STRATEGY_STORE,
    extract_strategies_from_file,
    load_extracted_strategies,
    save_extracted_strategies,
    delete_extracted_strategy,
)
from data2mcp_v2.utils.clogger import setup_logger
from data2mcp_v2.utils.config import omega_conf_to_dataclass
from data2mcp_v2.utils.llm_api import ChatModel

setup_logger(
    Path("./logs"),
    "root",
    file_name="api.log",
    stream_level=logging.DEBUG,
    file_level=logging.DEBUG,
)

logger = logging.getLogger(__name__)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[],
    allow_origin_regex=r".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载图表静态文件目录
charts_dir = os.path.join(os.getcwd(), "output", "charts")
os.makedirs(charts_dir, exist_ok=True)
app.mount("/charts", StaticFiles(directory=charts_dir), name="charts")


class ChatRequest(BaseModel):
    message: str
    config: dict[str, Any]
    history: list[dict[str, str]] = []


class SummaryRequest(BaseModel):
    config: dict[str, Any]


class ExtractStrategyRequest(BaseModel):
    file_path: str                        # absolute or relative path to PDF/TXT
    config: dict[str, Any]               # LLM config (same shape as chat config)
    max_pages: int = 50                  # PDF page limit
    chunk_size: int = 3000               # chars per LLM chunk


class DeleteStrategyRequest(BaseModel):
    key: str


@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        cfg = OmegaConf.create(request.config)
        cfg = omega_conf_to_dataclass(cfg)
        logger.debug(f"Received chat request with config: {cfg}")
        router = Router(cfg)
        final_text, message = await router.route(request.message)
        logger.debug(final_text)

        # 把本次生成的图表嵌入最终答案末尾（供评估器识别visualization得分）
        chart_paths = getattr(router, "generated_chart_paths", [])
        if chart_paths:
            chart_section = "\n\n## Visualizations\n"
            for cp in chart_paths:
                import os as _os
                fname = _os.path.basename(cp)
                title = _os.path.splitext(fname)[0].replace("_", " ")
                chart_section += f"\n![{title}]({cp})\n"
            final_text = final_text + chart_section

        return {
            "final_text": final_text,
            "messages": message,
            "strategy_used": getattr(router, "strategy_used", ""),
            "output_compliance_score": getattr(router, "output_compliance_score", None),
            "chart_paths": chart_paths,
        }

    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/data-summary")
async def data_summary_endpoint(request: SummaryRequest):
    try:
        cfg = OmegaConf.create(request.config)
        cfg = omega_conf_to_dataclass(cfg)
        summary = build_data_summary(cfg)
        return summary
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/strategies")
async def list_strategies_endpoint():
    """Return all active strategies (built-in + extracted)."""
    try:
        catalog = load_strategies()
        return {
            "strategies": [
                {
                    "key": spec.key,
                    "name": spec.name,
                    "description": spec.description,
                    "full_text": spec.full_text,
                    "source": spec.source,
                }
                for spec in catalog.values()
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/extract-strategies")
async def extract_strategies_endpoint(request: ExtractStrategyRequest):
    """
    Extract analytical strategies from a PDF or text file using LLM,
    persist them to the strategy store, and return the newly extracted strategies.
    """
    try:
        cfg = OmegaConf.create(request.config)
        cfg = omega_conf_to_dataclass(cfg)
        llm = ChatModel(
            model_name=cfg.llm.model,
            model_url=cfg.llm.base_url,
            api_key=cfg.llm.api_key,
            temperature=cfg.llm.temperature,
            max_tokens=cfg.llm.max_tokens,
            timeout=cfg.llm.timeout_seconds,
        )
        raw_strategies = extract_strategies_from_file(
            file_path=request.file_path,
            llm_client=llm,
            max_pages=request.max_pages,
            chunk_size=request.chunk_size,
        )
        final = save_extracted_strategies(raw_strategies, merge=True)
        logger.info("Extracted %d strategies from '%s'", len(raw_strategies), request.file_path)
        return {
            "extracted_count": len(raw_strategies),
            "total_stored": len(final),
            "strategies": raw_strategies,
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/strategies/{key}")
async def delete_strategy_endpoint(key: str):
    """Remove an extracted strategy by key."""
    removed = delete_extracted_strategy(key)
    if not removed:
        raise HTTPException(status_code=404, detail=f"Strategy '{key}' not found")
    return {"deleted": key}


@app.delete("/api/strategies-by-source")
async def delete_strategies_by_source_endpoint(source: str):
    """Remove all extracted strategies from a given source file."""
    existing = load_extracted_strategies()
    kept = [s for s in existing if s.get("source") != source]
    removed_count = len(existing) - len(kept)
    if removed_count == 0:
        raise HTTPException(status_code=404, detail=f"No strategies found for source '{source}'")
    save_extracted_strategies(kept, merge=False)
    return {"source": source, "deleted_count": removed_count}


@app.post("/api/upload-and-extract")
async def upload_and_extract_endpoint(
    file: UploadFile = File(...),
    config: str = Form(...),
    max_pages: int = Form(30),
    chunk_size: int = Form(3000),
):
    """
    Accept a file upload (PDF/TXT/MD), extract strategies via LLM,
    persist them, and return the newly extracted strategies.
    config is passed as a JSON string in the form field.
    """
    import json

    suffix = Path(file.filename or "upload.pdf").suffix.lower() or ".pdf"
    allowed = {".pdf", ".txt", ".md", ".rst"}
    if suffix not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{suffix}'. Allowed: {', '.join(allowed)}",
        )

    tmp_path = None
    try:
        # Save upload to a temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name

        cfg_dict = json.loads(config)
        cfg = OmegaConf.create(cfg_dict)
        cfg = omega_conf_to_dataclass(cfg)
        llm = ChatModel(
            model_name=cfg.llm.model,
            model_url=cfg.llm.base_url,
            api_key=cfg.llm.api_key,
            temperature=cfg.llm.temperature,
            max_tokens=cfg.llm.max_tokens,
            timeout=cfg.llm.timeout_seconds,
        )
        raw_strategies = extract_strategies_from_file(
            file_path=tmp_path,
            llm_client=llm,
            max_pages=max_pages,
            chunk_size=chunk_size,
        )
        # Attach original filename as source
        for s in raw_strategies:
            s["source"] = file.filename or "uploaded_file"

        final = save_extracted_strategies(raw_strategies, merge=True)
        logger.info(
            "Uploaded '%s': extracted %d strategies", file.filename, len(raw_strategies)
        )
        return {
            "extracted_count": len(raw_strategies),
            "total_stored": len(final),
            "strategies": raw_strategies,
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


if __name__ == "__main__":
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=2733)
    args = parser.parse_args()
    uvicorn.run(app, host="0.0.0.0", port=args.port)
