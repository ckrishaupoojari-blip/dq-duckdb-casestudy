function Step($title, $say) {
    Clear-Host
    Write-Host "=== $title ===" -ForegroundColor Cyan
    Write-Host "SAY: $say" -ForegroundColor Yellow
    Read-Host "Press Enter to run" | Out-Null
}

Step "1. Dataset" "2 million synthetic orders with defects injected on purpose. Nulls, bad emails, negative amounts, duplicates."
python src/00_show_data.py
Read-Host "Enter for next"

Step "2. Quality checks, clean and quarantine" "Nine rules across five quality dimensions. Raw data fails, clean data passes 100%."
python src/03_quality_checks.py
Read-Host "Enter for next"

Step "3. Live API monitoring (bonus)" "Real weather data from Open-Meteo, validated and logged to a history table."
python src/05_realtime_api.py 2 10
Read-Host "Enter for next"

Step "4. Monitoring dashboard" "All results from DuckDB history tables in one view."
python src/07_dq_dashboard.py
Read-Host "Enter for next"

Step "5. Optimisation" "Parquet vs CSV, partitioning, caching and threads."
Start-Process results\benchmark.png
Read-Host "Enter for next"

Step "6. Kubernetes (bonus)" "Same pipeline as a Job with CPU and memory limits, plus a CronJob for scheduled monitoring."
kubectl delete job dq-job dq-api-manual --ignore-not-found
kubectl get nodes
kubectl apply -f k8s/job.yaml
kubectl wait --for=condition=complete job/dq-job --timeout=600s
kubectl logs job/dq-job | Select-Object -Last 6
kubectl get pods,jobs
kubectl apply -f k8s/cronjob.yaml
kubectl create job --from=cronjob/dq-api-monitor dq-api-manual
kubectl wait --for=condition=complete job/dq-api-manual --timeout=120s
kubectl logs job/dq-api-manual
Read-Host "Enter for next"

Step "7. Performance comparison (bonus)" "pandas vs DuckDB with 1 thread vs 8 threads."
python src/06_compare_modes.py
Read-Host "Enter for the end"

Write-Host "Done. Open the GitHub repo page now." -ForegroundColor Green