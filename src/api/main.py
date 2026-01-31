"""
FastAPI 服務 - VB to Java Migration API

功能：
1. POST /analyze - 分析 VB 專案
2. POST /translate - 翻譯程式碼 (SSE 串流)
3. GET /status/{job_id} - 查詢任務狀態
4. GET /stream/{job_id} - SSE 串流進度
"""

import asyncio
import uuid
from typing import Dict, Optional, Any
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from ..analyzer import analyze_project
from ..parsers import VBScanner, VBParser
from ..extractors import SQLExtractor, SchemaInferrer, BusinessLogicExtractor
from ..generators import JavaProjectGenerator, JavaProjectConfig
from ..verifiers import BehaviorVerifier
from ..llm import create_llm_client, LLMConfig
from ..config.settings import get_settings


# ========== Pydantic Models ==========

class AnalyzeRequest(BaseModel):
    """分析請求"""
    project_path: str = Field(..., description="VB 專案路徑")
    output_dir: Optional[str] = Field(None, description="輸出目錄")
    recursive: bool = Field(True, description="是否遞迴掃描子目錄")


class TranslateRequest(BaseModel):
    """翻譯請求"""
    vb_code: str = Field(..., description="VB 程式碼")
    function_name: str = Field(..., description="函數名稱")
    target_layer: str = Field("usecase", description="目標層級: entity, usecase, repository, controller")
    context: Optional[str] = Field(None, description="額外上下文")


class GenerateProjectRequest(BaseModel):
    """生成專案請求"""
    project_path: str = Field(..., description="VB 專案路徑")
    output_dir: str = Field(..., description="輸出目錄")
    group_id: str = Field("com.example", description="Maven Group ID")
    artifact_id: str = Field("migrated-app", description="Maven Artifact ID")
    base_package: str = Field("com.example.app", description="基礎 Package")


class JobStatus(str, Enum):
    """任務狀態"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Job:
    """任務"""
    id: str
    status: JobStatus
    task_type: str
    created_at: datetime
    result: Optional[Any] = None
    error: Optional[str] = None
    progress: int = 0
    progress_message: str = ""


# ========== App Setup ==========

app = FastAPI(
    title="VB to Java Migration API",
    description="AI 驅動的 VB 專案遷移工具 API",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 任務存儲
jobs: Dict[str, Job] = {}

# SSE 事件佇列
sse_queues: Dict[str, asyncio.Queue] = {}


# ========== Helper Functions ==========

def create_job(task_type: str) -> Job:
    """建立新任務"""
    job_id = str(uuid.uuid4())
    job = Job(
        id=job_id,
        status=JobStatus.PENDING,
        task_type=task_type,
        created_at=datetime.now(),
    )
    jobs[job_id] = job
    sse_queues[job_id] = asyncio.Queue()
    return job


async def send_sse_event(job_id: str, event: str, data: str):
    """發送 SSE 事件"""
    if job_id in sse_queues:
        await sse_queues[job_id].put(f"event: {event}\ndata: {data}\n\n")


async def sse_generator(job_id: str):
    """SSE 事件生成器"""
    if job_id not in sse_queues:
        yield f"event: error\ndata: Job not found\n\n"
        return
    
    queue = sse_queues[job_id]
    
    while True:
        try:
            message = await asyncio.wait_for(queue.get(), timeout=30.0)
            yield message
            
            # 檢查任務是否結束
            if job_id in jobs:
                job = jobs[job_id]
                if job.status in [JobStatus.COMPLETED, JobStatus.FAILED]:
                    break
        except asyncio.TimeoutError:
            # 發送 heartbeat
            yield f"event: heartbeat\ndata: ping\n\n"


# ========== API Routes ==========

@app.get("/")
async def root():
    """API 根路徑"""
    return {
        "name": "VB to Java Migration API",
        "version": "1.0.0",
        "endpoints": {
            "POST /analyze": "分析 VB 專案",
            "POST /translate": "翻譯程式碼 (SSE)",
            "POST /generate": "生成 Java 專案",
            "GET /status/{job_id}": "查詢任務狀態",
            "GET /stream/{job_id}": "SSE 串流進度",
        }
    }


@app.post("/analyze")
async def analyze(request: AnalyzeRequest, background_tasks: BackgroundTasks):
    """
    分析 VB 專案
    
    返回任務 ID，可通過 /status/{job_id} 查詢狀態
    """
    project_path = Path(request.project_path)
    if not project_path.exists():
        raise HTTPException(status_code=400, detail=f"專案路徑不存在: {request.project_path}")
    
    job = create_job("analyze")
    
    async def run_analysis():
        try:
            job.status = JobStatus.RUNNING
            await send_sse_event(job.id, "status", "開始分析...")
            
            # 執行分析
            output_dir = request.output_dir or str(project_path / "output")
            result = analyze_project(
                str(project_path),
                output_dir,
                recursive=request.recursive,
            )
            
            job.status = JobStatus.COMPLETED
            job.result = result
            await send_sse_event(job.id, "complete", "分析完成")
            
        except Exception as e:
            job.status = JobStatus.FAILED
            job.error = str(e)
            await send_sse_event(job.id, "error", str(e))
    
    background_tasks.add_task(run_analysis)
    
    return {"job_id": job.id, "status": job.status.value}


@app.post("/translate")
async def translate(request: TranslateRequest):
    """
    翻譯 VB 程式碼為 Java (SSE 串流)
    
    返回 SSE 事件流，包含即時翻譯進度
    """
    settings = get_settings()
    
    if not settings.openai_api_key:
        raise HTTPException(status_code=400, detail="需要設定 OPENAI_API_KEY")
    
    from ..llm.java_translator import JavaLayer
    
    # 解析目標層級
    layer_map = {
        "entity": JavaLayer.ENTITY,
        "usecase": JavaLayer.USE_CASE,
        "repository": JavaLayer.REPOSITORY,
        "controller": JavaLayer.CONTROLLER,
        "dto": JavaLayer.DTO,
    }
    target_layer = layer_map.get(request.target_layer.lower(), JavaLayer.USE_CASE)
    
    async def generate_stream():
        try:
            llm_client = create_llm_client(
                api_key=settings.openai_api_key,
                base_url=settings.llm_base_url,
                model=settings.llm_model,
            )
            
            from ..llm import JavaCodeTranslator
            translator = JavaCodeTranslator(llm_client)
            
            # 發送開始事件
            yield f"event: start\ndata: 開始翻譯 {request.function_name}\n\n"
            
            # 收集串流內容
            full_content = []
            
            async def on_chunk(chunk: str):
                full_content.append(chunk)
            
            # 執行翻譯
            result = await translator.translate_function(
                vb_code=request.vb_code,
                function_name=request.function_name,
                target_layer=target_layer,
                context=request.context,
                on_chunk=on_chunk,
            )
            
            # 逐塊發送內容
            for chunk in full_content:
                yield f"event: chunk\ndata: {chunk}\n\n"
                await asyncio.sleep(0.01)  # 小延遲確保順序
            
            # 發送完成事件
            yield f"event: complete\ndata: 翻譯完成\n\n"
            
        except Exception as e:
            yield f"event: error\ndata: {str(e)}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@app.post("/generate")
async def generate_project(request: GenerateProjectRequest, background_tasks: BackgroundTasks):
    """
    生成完整的 Java 專案
    
    從 VB 專案分析結果生成 Clean Architecture Java 專案
    """
    project_path = Path(request.project_path)
    if not project_path.exists():
        raise HTTPException(status_code=400, detail=f"專案路徑不存在: {request.project_path}")
    
    job = create_job("generate")
    
    async def run_generation():
        try:
            job.status = JobStatus.RUNNING
            await send_sse_event(job.id, "status", "掃描 VB 檔案...")
            job.progress = 10
            
            # 掃描 VB 檔案
            scanner = VBScanner(str(project_path))
            vb_files = scanner.scan(recursive=True)
            
            await send_sse_event(job.id, "status", f"發現 {len(vb_files)} 個 VB 檔案")
            job.progress = 20
            
            # 解析 VB 檔案
            parser = VBParser()
            for vb_file in vb_files:
                parser.parse(vb_file)
            
            await send_sse_event(job.id, "status", "萃取 SQL 和 Schema...")
            job.progress = 40
            
            # 萃取 SQL
            sql_extractor = SQLExtractor()
            for vb_file in vb_files:
                if vb_file.module:
                    for func in vb_file.module.functions:
                        sql_extractor.extract_from_code(
                            func.body,
                            vb_file.filename,
                            func.name
                        )
            
            # 推斷 Schema
            schema_inferrer = SchemaInferrer()
            schema_inferrer.process_sql_extractor_results(sql_extractor)
            schema_inferrer.infer_additional_types()
            
            await send_sse_event(job.id, "status", "生成 Java 專案...")
            job.progress = 60
            
            # 生成 Java 專案
            config = JavaProjectConfig(
                group_id=request.group_id,
                artifact_id=request.artifact_id,
                base_package=request.base_package,
            )
            
            generator = JavaProjectGenerator(config=config)
            
            def on_progress(msg: str, current: int, total: int):
                job.progress_message = msg
                job.progress = 60 + int((current / total) * 30) if total > 0 else 70
            
            generated_files = generator.generate_from_schema(
                schema_inferrer,
                request.output_dir,
                on_progress=on_progress,
            )
            
            await send_sse_event(job.id, "status", f"生成完成: {len(generated_files)} 個檔案")
            job.progress = 100
            
            job.status = JobStatus.COMPLETED
            job.result = {
                "total_files": len(generated_files),
                "output_dir": request.output_dir,
                "summary": generator.get_summary(),
            }
            await send_sse_event(job.id, "complete", "專案生成完成")
            
        except Exception as e:
            job.status = JobStatus.FAILED
            job.error = str(e)
            await send_sse_event(job.id, "error", str(e))
    
    background_tasks.add_task(run_generation)
    
    return {"job_id": job.id, "status": job.status.value}


@app.get("/status/{job_id}")
async def get_status(job_id: str):
    """查詢任務狀態"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="任務不存在")
    
    job = jobs[job_id]
    
    return {
        "job_id": job.id,
        "status": job.status.value,
        "task_type": job.task_type,
        "progress": job.progress,
        "progress_message": job.progress_message,
        "created_at": job.created_at.isoformat(),
        "result": job.result if job.status == JobStatus.COMPLETED else None,
        "error": job.error if job.status == JobStatus.FAILED else None,
    }


@app.get("/stream/{job_id}")
async def stream_progress(job_id: str):
    """SSE 串流任務進度"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="任務不存在")
    
    return StreamingResponse(
        sse_generator(job_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@app.get("/health")
async def health_check():
    """健康檢查"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}
