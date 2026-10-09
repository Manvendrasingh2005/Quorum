"""Quick end-to-end test of the multi-agent pipeline."""
from src.orchestrator.supervisor import Supervisor

topic = "What are the latest trends in prompt engineering for LLMs in 2026"

print("Starting test run...")
supervisor = Supervisor()
result = supervisor.run(topic)

print("\n\n" + "=" * 50)
print("REPORT (first 500 chars):")
print("=" * 50)
print(result.report[:500])

print("\n" + "=" * 50)
print("METRICS:")
print("=" * 50)
for k, v in result.metrics.items():
    print(f"  {k}: {v}")

print("\n" + "=" * 50)
print("FINDINGS SUMMARY:")
print("=" * 50)
for f in result.findings:
    scores = f.critic_scores
    approved = scores.approved if scores else "N/A"
    grounding = f"{scores.grounding_score:.1f}" if scores else "N/A"
    print(f"  Q: {f.question[:60]}...")
    print(f"    Attempts: {f.critic_attempts} | Approved: {approved} | Grounding: {grounding}")
