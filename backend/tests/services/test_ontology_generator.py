from app.services.ontology_generator import OntologyGenerator


class CapturingLLMClient:
    def __init__(self):
        self.calls = []

    def chat_json(self, *args, **kwargs):
        self.calls.append({"args": args, "kwargs": kwargs})
        return {
            "entity_types": [
                {"name": "ProductConcept", "description": "Product concept", "attributes": []},
                {"name": "Person", "description": "Person", "attributes": []},
                {"name": "Organization", "description": "Organization", "attributes": []},
            ],
            "edge_types": [],
            "analysis_summary": "ok",
        }


def test_ontology_generation_uses_large_json_token_budget():
    client = CapturingLLMClient()
    generator = OntologyGenerator(llm_client=client)

    generator.generate(["舒客色修牙膏测试"], "评估消费者接受度")

    assert client.calls[0]["kwargs"]["max_tokens"] >= 8192
