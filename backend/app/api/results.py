"""
Results API Routes
"""
import csv
import io
import json
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db import crud
from app.models.schemas import (
    ResultResponse, SampleResultResponse, SampleResultListResponse,
    MetricsByType
)

router = APIRouter(prefix="/results", tags=["Results"])


@router.get("/{result_id}", response_model=ResultResponse)
async def get_result(
    result_id: str,
    db: AsyncSession = Depends(get_db)
):
    """获取检测结果"""
    result = await crud.get_result(db, result_id)
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")
    return ResultResponse.from_orm_with_metrics(result)


@router.get("/task/{task_id}", response_model=ResultResponse)
async def get_result_by_task(
    task_id: str,
    db: AsyncSession = Depends(get_db)
):
    """根据任务ID获取检测结果"""
    result = await crud.get_result_by_task(db, task_id)
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")
    return ResultResponse.from_orm_with_metrics(result)


@router.get("/{result_id}/samples", response_model=SampleResultListResponse)
async def get_sample_results(
    result_id: str,
    machine_type: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """获取样本检测结果"""
    result = await crud.get_result(db, result_id)
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")

    samples = await crud.get_sample_results(
        db,
        result_id,
        skip=skip,
        limit=limit,
        machine_type=machine_type
    )

    return SampleResultListResponse(
        total=len(samples),
        items=[SampleResultResponse.model_validate(s) for s in samples]
    )


@router.get("/{result_id}/export")
async def export_result(
    result_id: str,
    format: str = "csv",
    db: AsyncSession = Depends(get_db)
):
    """导出检测结果"""
    result = await crud.get_result(db, result_id)
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")

    samples = await crud.get_sample_results(db, result_id, limit=10000)

    if format == "csv":
        # 生成 CSV
        output = io.StringIO()
        writer = csv.writer(output)

        # 写入表头
        writer.writerow([
            "index", "section", "machine_type", "domain",
            "score", "label", "filename"
        ])

        # 写入数据
        for sample in samples:
            writer.writerow([
                sample.sample_index,
                sample.section,
                sample.machine_type,
                sample.domain,
                sample.score,
                sample.label,
                sample.filename
            ])

        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=result_{result_id}.csv"
            }
        )

    elif format == "json":
        # 生成 JSON
        data = {
            "result_id": result_id,
            "overall": result.overall,
            "auc_source": result.auc_source,
            "auc_target": result.auc_target,
            "p_auc": result.p_auc,
            "metrics_by_type": json.loads(result.metrics_json),
            "samples": [
                {
                    "index": s.sample_index,
                    "section": s.section,
                    "machine_type": s.machine_type,
                    "domain": s.domain,
                    "score": s.score,
                    "label": s.label,
                    "filename": s.filename
                }
                for s in samples
            ]
        }

        output = io.StringIO()
        json.dump(data, output, indent=2)
        output.seek(0)

        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename=result_{result_id}.json"
            }
        )

    else:
        raise HTTPException(status_code=400, detail="Unsupported format. Use 'csv' or 'json'")


@router.get("/{result_id}/distribution")
async def get_score_distribution(
    result_id: str,
    bins: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """获取分数分布数据"""
    import numpy as np

    result = await crud.get_result(db, result_id)
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")

    samples = await crud.get_sample_results(db, result_id, limit=10000)
    scores = [s.score for s in samples]
    labels = [s.label for s in samples]

    # 计算直方图
    scores_np = np.array(scores)
    counts, bin_edges = np.histogram(scores_np, bins=bins)

    # 分别计算正常和异常的分布
    normal_scores = [s for s, l in zip(scores, labels) if l == 0]
    anomaly_scores = [s for s, l in zip(scores, labels) if l == 1]

    normal_counts, _ = np.histogram(normal_scores, bins=bin_edges) if normal_scores else ([], bin_edges)
    anomaly_counts, _ = np.histogram(anomaly_scores, bins=bin_edges) if anomaly_scores else ([], bin_edges)

    return {
        "bin_edges": bin_edges.tolist(),
        "bin_centers": ((bin_edges[:-1] + bin_edges[1:]) / 2).tolist(),
        "counts": counts.tolist(),
        "normal_counts": normal_counts.tolist() if len(normal_counts) > 0 else [],
        "anomaly_counts": anomaly_counts.tolist() if len(anomaly_counts) > 0 else [],
        "total_samples": len(scores),
        "normal_samples": len(normal_scores),
        "anomaly_samples": len(anomaly_scores)
    }


@router.get("/{result_id}/roc")
async def get_roc_curve(
    result_id: str,
    db: AsyncSession = Depends(get_db)
):
    """获取 ROC 曲线数据"""
    from sklearn.metrics import roc_curve, auc
    import numpy as np

    result = await crud.get_result(db, result_id)
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")

    samples = await crud.get_sample_results(db, result_id, limit=10000)
    scores = np.array([s.score for s in samples])
    labels = np.array([s.label for s in samples])

    # 计算 ROC 曲线
    fpr, tpr, thresholds = roc_curve(labels, scores)
    roc_auc = auc(fpr, tpr)

    return {
        "fpr": fpr.tolist(),
        "tpr": tpr.tolist(),
        "thresholds": thresholds.tolist(),
        "auc": float(roc_auc)
    }
