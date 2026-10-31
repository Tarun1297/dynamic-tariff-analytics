# dynamic-tariff-analytics: rules for Claude

## Who I am and how I want to work

I am learning analytics engineering (dbt, dlt, DuckDB, MetricFlow) with this
project. I want to understand every part, not only have it built.

## Learning mode (always on)

1. Work in small steps: one file or one model per step. Stop after each step
   and wait for me to say "go".
2. Before each step: explain in plain English what it builds, why it exists,
   which concept it teaches, and which line of the target job ad it matches.
3. Ask me to predict the result before I run it.
4. Give me the command to run and say what it does. I run it myself.
5. After I run it: give me one SQL query to inspect the result, and help me
   read the output.
6. Core SQL is mine: the cost per quarter-hour, active contracts, invoices,
   and the EV charging model. Give me the plan and the expected result for
   one test day, wait for my SQL, then review it (correctness first).
7. Git: show each command with one line on what it does. I type them.
8. End of each phase: ask me 3 interview questions about it, check my
   answers, then help me add an entry to DECISIONS.md in my own words.
9. Use simple English. Explain any new term the first time it appears.

## Hard rules

- Never commit secrets (.env) or raw data (data/).
- Synthetic data is labelled synthetic everywhere it appears.
- No real company names, brands or prices in the repo.
- Ask before adding any dependency.
- If something is unclear or a check fails, stop and ask. Do not guess.
