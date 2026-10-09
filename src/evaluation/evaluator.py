"""
Evaluator Orchestrator.

Runs the test dataset through both a basic Gemini call (Baseline) 
and the full Multi-Agent pipeline, then scores both with the LLMJudge.
Saves the results to JSON for visualization.
"""
import json
import time
from pathlib import Path

from google import genai
from src.config import GEMINI_API_KEY
from src.orchestrator.supervisor import Supervisor
from src.evaluation.judge import LLMJudge

class Evaluator:
    def __init__(self):
        self.supervisor = Supervisor(on_status=lambda _: None) # quiet mode for supervisor
        self.judge = LLMJudge()
        self.client = genai.Client(api_key=GEMINI_API_KEY)
        self.dataset_path = Path(__file__).parent / "eval_dataset.json"
        
    def _run_baseline(self, topic: str) -> dict:
        """Run a standard, single-prompt LLM call as the baseline."""
        start_time = time.time()
        
        # A basic prompt simulating standard ChatGPT/Gemini usage
        prompt = f"Please write a well-researched report on: {topic}. Include source URLs if possible."
        response = self.client.models.generate_content(
            model="gemini-3.8-flash",  # Use the same primary model 
            contents=prompt
        )
        
        latency = time.time() - start_time
        return {
            "report": response.text,
            "latency_seconds": latency,
            "model_calls": 1
        }
        
    def _run_multiagent(self, topic: str) -> dict:
        """Run the full multi-agent pipeline."""
        start_time = time.time()
        result = self.supervisor.run_async(topic)
        latency = time.time() - start_time
        
        return {
            "report": result.report,
            "latency_seconds": latency,
            "model_calls": result.metrics.get("model_calls", 0),
            "critic_rejections": result.metrics.get("critic_rejections", 0)
        }

    def run_evaluation(self, num_samples: int = 5, output_file: str = "evaluation_results.json"):
        """Run the evaluation framework on a subset of the dataset."""
        with open(self.dataset_path, 'r', encoding='utf-8') as f:
            dataset = json.load(f)
            
        dataset = dataset[:num_samples]
        results = []
        
        print(f"🚀 Starting evaluation of {len(dataset)} queries...")
        print("-" * 50)
        
        for i, topic in enumerate(dataset, 1):
            print(f"[{i}/{len(dataset)}] Evaluating: {topic}")
            
            # 1. Baseline
            print("  ▶ Running Baseline...")
            baseline_data = self._run_baseline(topic)
            print("  ▶ Judging Baseline...")
            baseline_score = self.judge.evaluate(topic, baseline_data["report"])
            
            # 2. Multi-Agent
            print("  ▶ Running Multi-Agent Pipeline...")
            try:
                ma_data = self._run_multiagent(topic)
                print("  ▶ Judging Multi-Agent Pipeline...")
                ma_score = self.judge.evaluate(topic, ma_data["report"])
            except Exception as e:
                print(f"  ❌ Multi-Agent crashed: {e}")
                ma_data = {"report": f"FAILED: {e}", "latency_seconds": 0, "model_calls": 0, "critic_rejections": 0}
                ma_score = self.judge.evaluate(topic, "Failed to generate report.")
            
            # 3. Record
            res = {
                "topic": topic,
                "baseline": {
                    "latency": baseline_data["latency_seconds"],
                    "model_calls": baseline_data["model_calls"],
                    "scores": baseline_score.model_dump()
                },
                "multiagent": {
                    "latency": ma_data["latency_seconds"],
                    "model_calls": ma_data["model_calls"],
                    "critic_rejections": ma_data.get("critic_rejections", 0),
                    "scores": ma_score.model_dump()
                }
            }
            results.append(res)
            
            # Periodically save 
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2)
                
            print(f"  ✅ Done. Margin (Factual): {ma_score.factual_accuracy - baseline_score.factual_accuracy}")
            
        print("-" * 50)
        print(f"🎉 Evaluation complete! Results saved to {output_file}")


if __name__ == "__main__":
    evaluator = Evaluator()
    # Run a small subset by default to not burn through quota.
    evaluator.run_evaluation(num_samples=3)
