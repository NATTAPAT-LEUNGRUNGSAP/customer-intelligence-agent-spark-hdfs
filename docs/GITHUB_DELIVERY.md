# GitHub delivery

Project: Customer Intelligence Agent with Spark & HDFS
Repository name requested: customer-intelligence-agent-spark-hdfs
Owner: NATTAPAT-LEUNGRUNGSAP. Visibility authorized by user: Public.

Local Git initialized on main. Remote creation/publication still requires the
user's GitHub browser sign-in; the connector can read the account but cannot create
a repository. Do not treat this document as proof that a remote exists.

Publish source, knowledge, SQL, tests, Docker configuration, documentation and
selected reproducibility reports. Exclude downloaded datasets, model weights,
caches, .env/secrets, HDFS volumes, generated user query traces and temporary builds.
Archived v1 experiments remain local historical evidence and are not acceptance
criteria for the mandatory-RAG project.

Online Retail II is downloaded separately from UCI. Attribution:
Daqing Chen, Online Retail II, UCI Machine Learning Repository,
https://archive.ics.uci.edu/dataset/502/online+retail+ii .
The UCI dataset page lists CC BY 4.0 (verified 26 October 2026); retain attribution
when sharing derived data. Source archives are not redistributed in this repository.
No software license has been selected yet; public visibility does not grant a
software license by itself. Dependency licenses remain their respective owners'.

CI configuration runs Python unit tests only. Local runtime evidence uses Docker,
Spark, HDFS and Ollama/GPU; never call those checks GitHub CI results unless they
actually ran there. A fresh checkout must acquire data and produce its own passed
build manifest before web use; do not expect the original host's HDFS volumes.
