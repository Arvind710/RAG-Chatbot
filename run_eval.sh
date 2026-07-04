python -c "import yaml; yaml.safe_load(open('.github/workflows/daily_ingestion.yml')); print('✅ Valid YAML')"
grep -q 'schedule:' .github/workflows/daily_ingestion.yml && echo "✅ Cron schedule present" || echo "❌ Missing cron"
grep -q 'workflow_dispatch' .github/workflows/daily_ingestion.yml && echo "✅ Manual trigger present" || echo "❌ Missing manual trigger"
grep -q 'secrets.GROQ_API_KEY' .github/workflows/daily_ingestion.yml && echo "✅ Secrets configured" || echo "❌ Missing secrets"
grep -q 'github-actions\[bot\]' .github/workflows/daily_ingestion.yml && echo "✅ Bot identity set" || echo "❌ Missing bot identity"

echo "Running unit tests..."
source .venv/bin/activate && pytest tests/test_ci_ingestion.py -v --tb=short

echo "Running CI runner script locally (this may take a bit)..."
source .venv/bin/activate && python scripts/run_ingestion_ci.py

echo "Verifying ingestion log..."
python -c "
import json
try:
    log = json.load(open('data/ingestion_log.json'))
    entry = log[-1] if isinstance(log, list) else log
    required = ['timestamp', 'status', 'duration_seconds', 'chunks_count', 'error_message']
    missing = [f for f in required if f not in entry]
    if missing:
        print(f'❌ Missing fields: {missing}')
    else:
        print(f'✅ Log valid: {entry[\"status\"]} at {entry[\"timestamp\"]} ({entry[\"chunks_count\"]} chunks)')
except Exception as e:
    print(f'❌ Log error: {e}')
"
