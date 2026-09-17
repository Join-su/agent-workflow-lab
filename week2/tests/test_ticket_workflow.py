import unittest
from dataclasses import replace

from fastapi.testclient import TestClient

from week2.app import TicketRequest, create_app, create_fixture_services, run_ticket_workflow


class Week2TicketWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.services = create_fixture_services()
        self.client = TestClient(create_app(self.services))

    def test_billing_ticket_is_classified_and_planned(self):
        ticket = TicketRequest(
            subject="Duplicate invoice",
            description="I was charged twice and need a refund.",
            customer_tier="standard",
        )
        result = run_ticket_workflow(ticket, self.services)

        self.assertEqual(result["difficulty"], 2)
        self.assertEqual(result["mode"], "fixture")
        self.assertEqual(result["category"], "billing")
        self.assertEqual(result["route"], "billing_queue")
        self.assertEqual(result["status"], "plan_ready")
        self.assertTrue(result["resolution_plan"])
        self.assertEqual(result["citations"][0]["document_id"], "support-billing-playbook")
        self.assertEqual(result["steps"][-1], "billing_queue")

    def test_retrieval_filters_playbooks_by_classified_category(self):
        documents = self.services.retriever.search(
            "refund account error", k=5, filter={"category": "billing"}
        )

        self.assertTrue(documents)
        self.assertTrue(all(document.metadata["category"] == "billing" for document in documents))

    def test_access_ticket_routes_to_access_queue_with_access_citation(self):
        result = run_ticket_workflow(
            TicketRequest(
                subject="Login failure",
                description="My account login fails repeatedly.",
                customer_tier="standard",
            ),
            self.services,
        )
        self.assertEqual(result["route"], "access_queue")
        self.assertTrue(all("access" in item["document_id"] for item in result["citations"]))

    def test_fallback_ticket_handles_empty_category_retrieval(self):
        result = run_ticket_workflow(
            TicketRequest(
                subject="General question",
                description="Please explain your office hours.",
                customer_tier="standard",
            ),
            self.services,
        )
        self.assertEqual(result["category"], "other")
        self.assertEqual(result["route"], "general_queue")
        self.assertEqual(result["status"], "needs_more_information")
        self.assertEqual(result["citations"], [])
        self.assertTrue(result["resolution_plan"])

    def test_empty_retrieval_uses_deterministic_fallback_without_calling_planner(self):
        class EmptyRetriever:
            def search(self, query, *, k=3, filter=None):
                return []

        def fail_if_called(ticket, classification, documents):
            self.fail("planner must not run without grounded playbook evidence")

        services = replace(self.services, retriever=EmptyRetriever(), plan=fail_if_called)
        result = run_ticket_workflow(
            TicketRequest(
                subject="Account question",
                description="Please explain this unusual account issue.",
                customer_tier="standard",
            ),
            services,
        )

        self.assertEqual(result["status"], "needs_more_information")
        self.assertEqual(result["citations"], [])
        self.assertIn("Collect missing details", result["resolution_plan"])

    def test_outage_language_routes_to_urgent_escalation(self):
        ticket = TicketRequest(
            subject="Production outage",
            description="All users are blocked and the service is down.",
            customer_tier="enterprise",
        )
        result = run_ticket_workflow(ticket, self.services)

        self.assertEqual(result["priority"], "urgent")
        self.assertEqual(result["route"], "incident_escalation")
        self.assertEqual(
            result["steps"],
            ["classify", "retrieve_playbook", "plan_resolution", "route", "incident_escalation"],
        )

    def test_api_validates_customer_tier(self):
        response = self.client.post(
            "/tickets/plan",
            json={"subject": "Help", "description": "Login fails repeatedly", "customer_tier": "vip"},
        )
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
