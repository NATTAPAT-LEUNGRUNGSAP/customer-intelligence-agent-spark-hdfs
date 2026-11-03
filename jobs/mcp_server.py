"""Optional stdio MCP adapter. No arbitrary Python or unreviewed SQL endpoint."""
import argparse
import os
import json
from agent_tools import observe_tools
from pseudonymization import pseudonymize_result
from input_guard import validate_question


def create_server(schema, ask, key):
    from mcp.server.fastmcp import FastMCP
    server = FastMCP('customer-intelligence-pyspark')

    @server.tool()
    def list_tables() -> list[str]:
        """List allowlisted, registered PySpark analytics views; no row access."""
        return observe_tools({'tools':[{'name':'list_tables'}]}, schema)[0]['result']

    @server.tool()
    def describe_table(table: str) -> str:
        """Return the schema of one allowlisted analytics view."""
        result = observe_tools({'tools':[{'name':'describe_table','table':table}]}, schema)[0]['result']
        return json.dumps(result,ensure_ascii=False) if isinstance(result,dict) else result

    @server.tool()
    def analyze(question: str) -> dict:
        """Answer through mandatory RAG, SQL guards, reviewer and bounded PySpark."""
        response = ask(validate_question(question))
        # Deliberately exclude proposals, exceptions and SQL literals from export.
        exported = {'status':response['status'], 'citations':response.get('citations',[])}
        if response.get('result') is not None:
            exported['result'] = pseudonymize_result(response['result'], key)
        if response['status'] == 'clarification':
            exported['message'] = response.get('message','')
        return exported

    return server


def main():
    from pyspark.sql import SparkSession
    from agent import answer
    from query_runtime import load_views, run_query
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--knowledge', default='/app/knowledge')
    parser.add_argument('--require-read-only', action='store_true')
    args = parser.parse_args()
    key = os.environ.get('CUSTOMER_PSEUDONYM_KEY','').encode()
    pseudonymize_result({'columns':[], 'rows':[]}, key)
    model = os.environ.get('OLLAMA_MODEL')
    if not model:
        parser.error('OLLAMA_MODEL is required')
    spark = SparkSession.builder.appName('customer-intelligence-mcp').config(
        'spark.sql.session.timeZone','UTC').getOrCreate()
    try:
        schema, manifest = load_views(spark, args.manifest)
        from query_runtime import require_read_only
        require_read_only(spark, manifest['root'])
        server = create_server(schema, lambda question: answer(question, schema,
            lambda sql: run_query(spark, sql), model,
            os.environ.get('OLLAMA_URL','http://host.docker.internal:11434'), args.knowledge), key)
        server.run(transport='stdio')
    finally:
        spark.stop()


if __name__ == '__main__':
    main()
