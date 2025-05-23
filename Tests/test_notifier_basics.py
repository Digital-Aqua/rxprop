from rxprop.notifier import TriggerNotifier # Assuming this import path
from typing import Any

_handler1_call_count = 0
_handler2_call_count = 0

def mock_handler1():
    global _handler1_call_count
    _handler1_call_count += 1

def mock_handler2():
    global _handler2_call_count
    _handler2_call_count += 1

class TestNotifierHandlerManagement:
    def setup_method(self, method: Any):
        # Reset counters before each test method in this class
        global _handler1_call_count, _handler2_call_count
        _handler1_call_count = 0
        _handler2_call_count = 0

    def test_add_handler_then_registered(self):
        """Tests that add_handler registers a handler, verified by fire()."""
        n = TriggerNotifier()
        n.add_handler(mock_handler1)
        assert _handler1_call_count == 0
        n.fire()
        assert _handler1_call_count == 1
        n.fire()
        assert _handler1_call_count == 2

    def test_remove_handler_then_deregistered(self):
        """Tests that remove_handler deregisters a handler, verified by fire()."""
        n = TriggerNotifier()
        n.add_handler(mock_handler1)
        n.add_handler(mock_handler2)

        n.fire()
        assert _handler1_call_count == 1
        assert _handler2_call_count == 1

        n.remove_handler(mock_handler1)
        n.fire()
        assert _handler1_call_count == 1 # Not called again
        assert _handler2_call_count == 2 # mock_handler2 still active

        n.remove_handler(mock_handler2)
        n.fire()
        assert _handler1_call_count == 1 # Still 1
        assert _handler2_call_count == 2 # Not called again

    def test_remove_non_existent_handler_then_no_error(self):
        """Tests that remove_handler for a non-added handler does not error."""
        n = TriggerNotifier()
        try:
            n.remove_handler(mock_handler1) # mock_handler1 was never added
        except Exception as e:
            assert False, f"remove_handler raised an unexpected error: {e}"
        
        # Also test removing a handler that was added and then already removed
        n.add_handler(mock_handler2)
        n.remove_handler(mock_handler2)
        try:
            n.remove_handler(mock_handler2) # Removing again
        except Exception as e:
            assert False, f"remove_handler for already-removed handler raised an unexpected error: {e}"

    def test_fire_with_multiple_handlers_then_all_called(self):
        """Tests that fire() calls all registered handlers."""
        n = TriggerNotifier()
        n.add_handler(mock_handler1)
        n.add_handler(mock_handler2)

        n.fire()
        assert _handler1_call_count == 1
        assert _handler2_call_count == 1

        n.fire()
        assert _handler1_call_count == 2
        assert _handler2_call_count == 2

    def test_fire_with_no_handlers_then_no_error(self):
        """Tests that fire() on a Notifier with no handlers does not error."""
        n = TriggerNotifier()
        try:
            n.fire()
        except Exception as e:
            assert False, f"fire() with no handlers raised an unexpected error: {e}" 