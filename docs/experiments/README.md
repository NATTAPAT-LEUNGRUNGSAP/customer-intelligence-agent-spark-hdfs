# Retained context experiment implementation

context_engine_v1.py.txt is the original metadata-stripping evidence-packing module.
Its exact bytes match the jobs/context_engine.py SHA256 in
reports/context-v1-9d66b9e8b1ab45c7bef19fabaf693ae4.json.
It is retained as evidence for the candidate whose exposed regression fell to18/20,
not imported by the production application. The current module preserves the prior
model-facing evidence JSON instead. Replaying an old protocol with changed runtime
code must be labeled with the actual new fingerprints; it is not the original run.
