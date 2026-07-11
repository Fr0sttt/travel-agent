"""
Travel Agent 评估系统

提供5种评估框架，覆盖端到端质量、推理过程、工具调用、RAG效果和综合指标。

评估框架：
1. RACE (end_to_end)    - 端到端行程质量评估 (DeepResearch-Bench)
2. DoVer (reasoning)    - 推理过程评估 (DoVer框架)
3. AgentWorld (tool_use) - 工具调用评估 (Agent-World框架)
4. FACT (rag)           - RAG效果评估 (DeepResearch-Bench)
5. Comprehensive        - Travel Agent综合指标

Usage:
    from backend.app.evaluation import (
        EvaluationRunner,
        RACEEndToEndEvaluator,
        DoVerReasoningEvaluator,
        AgentWorldToolEvaluator,
        FACTRAGEvaluator,
        ComprehensiveMetricsEvaluator,
        EvalResult,
        EvalReport,
        BaseEvaluator,
    )

    # 快速评估
    runner = EvaluationRunner()
    report = await runner.run_full_evaluation(session_data)
    print(report.overall_score)
    print(report.dimension_scores)

    # 单项评估
    result = await runner.run_single_eval("end_to_end", data)

    # 导出报告
    json_str = runner.export_report(report, format="json")
    md_str = runner.export_report(report, format="md")
"""

try:
    from backend.app.evaluation.base import BaseEvaluator, EvalResult, EvalReport, DimensionWeight, ToolCallRecord, TrialSegment
    from backend.app.evaluation.end_to_end import RACEEndToEndEvaluator
    from backend.app.evaluation.reasoning_eval import DoVerReasoningEvaluator
    from backend.app.evaluation.tool_eval import AgentWorldToolEvaluator
    from backend.app.evaluation.rag_eval import FACTRAGEvaluator
    from backend.app.evaluation.comprehensive_metrics import ComprehensiveMetricsEvaluator
    from backend.app.evaluation.evaluation_runner import EvaluationRunner
except ModuleNotFoundError:
    from evaluation.base import BaseEvaluator, EvalResult, EvalReport, DimensionWeight, ToolCallRecord, TrialSegment
    from evaluation.end_to_end import RACEEndToEndEvaluator
    from evaluation.reasoning_eval import DoVerReasoningEvaluator
    from evaluation.tool_eval import AgentWorldToolEvaluator
    from evaluation.rag_eval import FACTRAGEvaluator
    from evaluation.comprehensive_metrics import ComprehensiveMetricsEvaluator
    from evaluation.evaluation_runner import EvaluationRunner

__all__ = [
    # 基类与数据结构
    "BaseEvaluator",
    "EvalResult",
    "EvalReport",
    "DimensionWeight",
    "ToolCallRecord",
    "TrialSegment",
    # 评估器
    "RACEEndToEndEvaluator",
    "DoVerReasoningEvaluator",
    "AgentWorldToolEvaluator",
    "FACTRAGEvaluator",
    "ComprehensiveMetricsEvaluator",
    # 运行器
    "EvaluationRunner",
]

__version__ = "1.0.0"
