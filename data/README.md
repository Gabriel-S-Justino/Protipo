# data/ (fora do Git, exceto limites pequenos)

- `raw/`       — CSVs baixos da FIRMS (cache por checksum; nunca versionar)
- `processed/` — tabelas intermediárias do pipeline
- `boundaries/`— malhas IBGE pequenas (limites) — versionável só com justificativa
- `reports/`   — relatórios de calibração e execução
- `demo/`      — trabalho de DEMO

⚠️ Nenhum dataset real deve ser commitado. Ver `.gitignore`.
