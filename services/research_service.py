"""HFOS v5.0 — Research Service"""
from engines.backtest_engine import BacktestEngine
from engines.walkforward_engine import WalkForwardEngine
from engines.monte_carlo_engine import MonteCarloEngine
from engines.benchmark_engine import BenchmarkEngine
from engines.factor_analysis_engine import FactorAnalysisEngine

class ResearchService:
    def run_full_suite(self, params: dict) -> dict:
        """Executes all institutional research engines."""
        bt = BacktestEngine().run(params)
        wf = WalkForwardEngine().validate(params)
        mc = MonteCarloEngine().run(params)
        bm = BenchmarkEngine().compare(bt["cagr"], 0)
        fa = FactorAnalysisEngine().analyze(params)
        
        # In a real system, you'd insert these into the SQLite DB (research_runs etc) here.
        return {
            "backtest": bt,
            "walkforward": wf,
            "monte_carlo": mc,
            "benchmark": bm,
            "factor_analysis": fa
        }
