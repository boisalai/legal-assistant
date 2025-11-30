"""Workflows module for Legal Assistant."""

from .summarize_judgment import SimpleJudgmentSummarizer, create_summarize_workflow, run_summarize_workflow

__all__ = ["SimpleJudgmentSummarizer", "create_summarize_workflow", "run_summarize_workflow"]
