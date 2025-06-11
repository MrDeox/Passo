import unittest
import re # For testing slug patterns if needed, though _generate_slug is in core_types
import uuid # For checking generated UUIDs in slugs
from dataclasses import is_dataclass, fields
import time # For checking timestamps

# Assuming your project structure allows this import:
# Adjust if your project uses a different structure (e.g., src directory)
from core_types import Ideia, Service, Task, _generate_slug

class TestGenerateSlug(unittest.TestCase):
    def test_basic_slug(self):
        self.assertEqual(_generate_slug("Simple Title"), "simple-title")

    def test_with_spaces_and_hyphens(self):
        self.assertEqual(_generate_slug("Title with  spaces -- and hyphens"), "title-with-spaces-and-hyphens")

    def test_with_special_chars(self):
        self.assertEqual(_generate_slug("Title with !@#$%^&*()_+ special chars?"), "title-with-special-chars")

    def test_lowercase(self):
        self.assertEqual(_generate_slug("UPPERCASE Title"), "uppercase-title")

    def test_max_length(self):
        long_title = "This is a very long title that definitely exceeds the fifty character limit for slugs"
        slug = _generate_slug(long_title)
        self.assertEqual(slug, "this-is-a-very-long-title-that-definitely-excee") # 50 chars
        self.assertTrue(len(slug) <= 50)

    def test_empty_string(self):
        self.assertEqual(_generate_slug(""), "untitled-idea")

    def test_only_special_chars(self):
        slug = _generate_slug("!@#$%^&*()")
        self.assertTrue(slug.startswith("untitled-idea-"))
        self.assertEqual(len(slug), len("untitled-idea-") + 6) # 6 hex chars from uuid

    def test_leading_trailing_hyphens(self):
        self.assertEqual(_generate_slug("-leading-and-trailing-"), "leading-and-trailing")

    def test_unicode_chars(self):
        # _generate_slug as implemented primarily targets ASCII,
        # unicode non-alphanumeric might be removed.
        # Example: "Idée Française" -> "idee-francaise" (if accents are removed by re.sub)
        # The current re.sub(r'[^\w\s-]', '', text.lower()) might strip accents.
        # This test depends on the exact behavior of `\w` with unicode in the regex context.
        # For simplicity, we test with common cases.
        self.assertEqual(_generate_slug("Idée Française"), "idee-francaise") # Assumes \w handles common accents or they are stripped

class TestIdeiaDataclass(unittest.TestCase):
    def test_ideia_creation_defaults(self):
        ideia = Ideia(descricao="Test Idea", justificativa="Justification", autor="Author")
        self.assertTrue(is_dataclass(ideia))
        self.assertEqual(ideia.descricao, "Test Idea")
        self.assertEqual(ideia.justificativa, "Justification")
        self.assertEqual(ideia.autor, "Author")
        self.assertFalse(ideia.validada)
        self.assertFalse(ideia.executada)
        self.assertEqual(ideia.resultado, 0.0)
        self.assertIsNone(ideia.link_produto)

    def test_ideia_slug_property(self):
        ideia1 = Ideia(descricao="My Awesome Idea!", justificativa="J", autor="A")
        self.assertEqual(ideia1.slug, "my-awesome-idea")

        ideia2 = Ideia(descricao="  Another idea with spaces  ", justificativa="J", autor="A")
        self.assertEqual(ideia2.slug, "another-idea-with-spaces")

        ideia3 = Ideia(descricao="!@#$", justificativa="J", autor="A")
        self.assertTrue(ideia3.slug.startswith("untitled-idea-"))

class TestServiceDataclass(unittest.TestCase):
    def test_service_creation_defaults(self):
        service = Service(service_name="Test Service", description="Desc", author="Auth")
        self.assertTrue(is_dataclass(service))
        self.assertIsNotNone(service.id)
        self.assertEqual(service.service_name, "Test Service")
        self.assertEqual(service.status, "proposed")
        self.assertEqual(len(service.history), 1) # __post_init__ adds one entry
        self.assertEqual(service.history[0]["status"], "proposed")
        self.assertEqual(service.history[0]["message"], "Service proposed")
        self.assertEqual(service.cycles_unassigned, 0)
        self.assertEqual(service.progress_hours, 0.0)
        self.assertFalse(service.revenue_calculated)

    def test_service_update_status(self):
        service = Service(service_name="S1", description="D1", author="A1")
        ts_before = time.time()
        service.update_status("validated", "Validated by system.")
        ts_after = time.time()

        self.assertEqual(service.status, "validated")
        self.assertEqual(len(service.history), 2)
        self.assertEqual(service.history[1]["status"], "validated")
        self.assertEqual(service.history[1]["message"], "Validated by system.")
        history_ts = float(service.history[1]["timestamp"])
        self.assertTrue(ts_before <= history_ts <= ts_after)
        self.assertIsNotNone(service.validation_timestamp)
        self.assertTrue(ts_before <= service.validation_timestamp <= ts_after)

        # Test invalid status
        service.update_status("invalid_status_value", "Trying invalid.")
        self.assertEqual(service.status, "validated") # Should not change
        self.assertEqual(len(service.history), 2) # No new history entry

    def test_service_assign_agent(self):
        service = Service(service_name="S2", description="D2", author="A2")
        service.update_status("validated", "Ready for assignment") # Must be validated first

        service.assign_agent("ExecutorBob", message="Assigned to Bob by test")
        self.assertEqual(service.status, "in_progress")
        self.assertEqual(service.assigned_agent_name, "ExecutorBob")
        self.assertEqual(service.progress_hours, 0.0)
        self.assertEqual(service.cycles_unassigned, 0)
        self.assertIsNotNone(service.delivery_start_timestamp)
        self.assertEqual(service.history[-1]["status"], "in_progress")
        self.assertEqual(service.history[-1]["message"], "Assigned to Bob by test")

        # Test assigning to non-validated service
        service2 = Service(service_name="S3", description="D3", author="A3")
        service2.assign_agent("ExecutorAlice") # Should not assign
        self.assertNotEqual(service2.status, "in_progress")
        self.assertIsNone(service2.assigned_agent_name)


    def test_service_complete_service(self):
        service = Service(service_name="S4", description="D4", author="A4")
        service.update_status("validated", "Validated")
        service.assign_agent("ExecutorCharlie")

        ts_before_complete = time.time()
        service.complete_service("Service finished by test.")
        ts_after_complete = time.time()

        self.assertEqual(service.status, "completed")
        self.assertIsNotNone(service.completion_timestamp)
        self.assertTrue(ts_before_complete <= service.completion_timestamp <= ts_after_complete)
        self.assertEqual(service.history[-1]["status"], "completed")
        self.assertEqual(service.history[-1]["message"], "Service finished by test.")

        # Test completing a non-in-progress service
        service2 = Service(service_name="S5", description="D5", author="A5")
        service2.complete_service() # Should not complete
        self.assertNotEqual(service2.status, "completed")


class TestTaskDataclass(unittest.TestCase):
    def test_task_creation_defaults(self):
        task = Task(description="Test Task")
        self.assertTrue(is_dataclass(task))
        self.assertIsNotNone(task.id)
        self.assertEqual(task.description, "Test Task")
        self.assertEqual(task.status, "todo")
        self.assertEqual(len(task.history), 0) # History starts empty

    def test_task_update_status(self):
        task = Task(description="T1")
        ts_before = time.time()
        task.update_status("in_progress", "Task started.")
        ts_after = time.time()

        self.assertEqual(task.status, "in_progress")
        self.assertEqual(len(task.history), 1)
        self.assertEqual(task.history[0]["status"], "in_progress")
        self.assertEqual(task.history[0]["message"], "Task started.")
        history_ts = float(task.history[0]["timestamp"])
        self.assertTrue(ts_before <= history_ts <= ts_after)

        task.update_status("done", "Task completed by test.")
        self.assertEqual(task.status, "done")
        self.assertEqual(len(task.history), 2)
        self.assertEqual(task.history[1]["status"], "done")

        # Test invalid status
        task.update_status("invalid_status_here", "Trying invalid.")
        self.assertEqual(task.status, "done") # Should not change
        self.assertEqual(len(task.history), 2) # No new history entry

if __name__ == '__main__':
    unittest.main()
