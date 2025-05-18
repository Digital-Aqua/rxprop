import pytest
from unittest.mock import MagicMock, patch
from typing import Any
import asyncio

from rxprop.reactive_property import ReactivePropertyMixin, listen_for_dependencies, _dep_ctx_stack, ReactiveProperty # type: ignore
from rxprop.notifier import Notifier
from rxprop.typed_property import TypedProperty, GetterMixin, SetterMixin

class MockOwner:
    pass

class TestListenForDependencies:
    def test_listen_adds_to_buffer(self):
        prop: ReactivePropertyMixin[Any, Any] = ReactivePropertyMixin()
        instance = MockOwner()
        
        mock_notifier = Notifier()
        prop._get_notifier = MagicMock(return_value=mock_notifier) # type: ignore

        buffer: set[Notifier] = set()
        assert len(_dep_ctx_stack) == 0

        with patch.object(TypedProperty, '_get', return_value="mocked_super_value") as mock_typed_property_get:
            with listen_for_dependencies(buffer):
                assert len(_dep_ctx_stack) == 1
                assert _dep_ctx_stack[0] is buffer
                prop.__get__(instance, MockOwner)

        assert len(_dep_ctx_stack) == 0
        assert len(buffer) == 1, f"Buffer has {len(buffer)} items, expected 1. Buffer: {buffer}"
        assert mock_notifier in buffer
        prop._get_notifier.assert_called_once_with(instance) # type: ignore
        mock_typed_property_get.assert_called_once_with(instance)

    def test_listen_stack_management(self):
        """Test _dep_ctx_stack is correctly managed (pushed on enter, popped on exit)."""
        buffer1: set[Notifier] = set()
        
        assert len(_dep_ctx_stack) == 0
        with listen_for_dependencies(buffer1):
            assert len(_dep_ctx_stack) == 1
            assert _dep_ctx_stack[0] is buffer1
            
            buffer2: set[Notifier] = set()
            with listen_for_dependencies(buffer2):
                assert len(_dep_ctx_stack) == 2
                assert _dep_ctx_stack[0] is buffer1
                assert _dep_ctx_stack[1] is buffer2
            
            assert len(_dep_ctx_stack) == 1
            assert _dep_ctx_stack[0] is buffer1
            
        assert len(_dep_ctx_stack) == 0

    def test_listen_stack_management_with_exception(self):
        """Test _dep_ctx_stack is correctly managed even with an exception."""
        buffer: set[Notifier] = set()
        
        assert len(_dep_ctx_stack) == 0
        with pytest.raises(ValueError):
            with listen_for_dependencies(buffer):
                assert len(_dep_ctx_stack) == 1
                assert _dep_ctx_stack[0] is buffer
                raise ValueError("Test exception")
        
        assert len(_dep_ctx_stack) == 0

    def test_listen_nested_contexts_dependencies_go_to_innermost(self):
        prop1: ReactivePropertyMixin[Any, Any] = ReactivePropertyMixin()
        prop2: ReactivePropertyMixin[Any, Any] = ReactivePropertyMixin()
        instance = MockOwner()

        notifier1 = Notifier()
        notifier2 = Notifier()
        prop1._get_notifier = MagicMock(return_value=notifier1) # type: ignore
        prop2._get_notifier = MagicMock(return_value=notifier2) # type: ignore

        outer_buffer: set[Notifier] = set()
        inner_buffer: set[Notifier] = set()

        with patch.object(TypedProperty, '_get', MagicMock(return_value="val1")) as mock_tp_get1:
            with listen_for_dependencies(outer_buffer):
                prop1.__get__(instance, MockOwner)

                with patch.object(TypedProperty, '_get', MagicMock(return_value="val2")) as mock_tp_get2:
                    with listen_for_dependencies(inner_buffer):
                        prop2.__get__(instance, MockOwner)
                    mock_tp_get2.assert_called_once_with(instance)
            
            mock_tp_get1.assert_called_once_with(instance)

        assert notifier2 not in outer_buffer
        assert notifier2 in inner_buffer, f"Notifier2 not in inner_buffer. Inner: {inner_buffer}"
        assert len(inner_buffer) == 1

        assert notifier1 in outer_buffer, f"Notifier1 not in outer_buffer. Outer: {outer_buffer}"
        assert len(outer_buffer) == 1
        assert notifier1 not in inner_buffer
        
        prop1._get_notifier.assert_called_once_with(instance) # type: ignore
        prop2._get_notifier.assert_called_once_with(instance) # type: ignore

class TestReactivePropertyMixin:

    class PropWithMixin(ReactivePropertyMixin[Any, Any], TypedProperty[Any, Any]): # type: ignore[misc]
        # A concrete class that uses the mixin for testing
        # It also needs a base TypedProperty for super() calls like _get, _set
        def __init__(self, fget: Any = None, fset: Any = None) -> None:
            super().__init__() # Calls ReactivePropertyMixin init, then TypedProperty init
            # These would typically be set by GetterMixin/SetterMixin decorators
            self.fget = fget 
            self.fset = fset

        # Mock implementations for TypedProperty methods if ReactivePropertyMixin calls super()
        _super_get_mock = MagicMock()
        _super_set_mock = MagicMock()

        def _get(self, instance: Any) -> Any:
            # This is the super()._get that ReactivePropertyMixin will call
            self._super_get_mock(instance)
            if self.fget:
                return self.fget(instance)
            return TypedProperty._get(self, instance) # Fallback to TypedProperty's default _get

        def _set(self, instance: Any, value: Any) -> None:
            # This is the super()._set that ReactivePropertyMixin will call
            self._super_set_mock(instance, value)
            if self.fset:
                self.fset(instance, value)
            else:
                TypedProperty._set(self, instance, value) # Fallback to TypedProperty's default _set


    def test_get_notifier_creates_and_caches(self):
        prop = TestReactivePropertyMixin.PropWithMixin()
        instance = MockOwner()

        notifier1 = prop._get_notifier(instance)
        assert isinstance(notifier1, Notifier), "Should create a Notifier"

        notifier2 = prop._get_notifier(instance)
        assert notifier1 is notifier2, "Should return cached Notifier"

        # Test WeakKeyDictionary behavior for _notifiers (indirectly)
        # Ensure a different instance gets a different notifier
        instance2 = MockOwner()
        notifier3 = prop._get_notifier(instance2)
        assert isinstance(notifier3, Notifier)
        assert notifier1 is not notifier3

        # Difficult to deterministically test GC and WeakKeyDictionary removal here,
        # but we verify it uses WeakKeyDictionary by checking that _notifiers exists
        # and is likely a WeakKeyDictionary as per implementation.
        assert hasattr(prop, '_notifiers')
        # from weakref import WeakKeyDictionary
        # assert isinstance(prop._notifiers, WeakKeyDictionary)
        pass # Further assertion if specific type check is desired and safe

    def test_mixin_get_registers_dependency_and_calls_super(self):
        prop = TestReactivePropertyMixin.PropWithMixin()
        instance = MockOwner()
        buffer: set[Notifier] = set()
        
        # Reset mocks from TypedProperty part of the PropWithMixin if they were class-level
        prop._super_get_mock.reset_mock()

        with listen_for_dependencies(buffer):
            prop.__get__(instance, MockOwner) # Calls ReactivePropertyMixin.__get__ -> _get

        assert len(buffer) == 1, "Notifier should be added to dependency buffer"
        assert prop._get_notifier(instance) in buffer
        prop._super_get_mock.assert_called_once_with(instance)

    def test_mixin_set_calls_super_and_fires_notifier(self):
        prop = TestReactivePropertyMixin.PropWithMixin()
        instance = MockOwner()
        
        # Reset mocks
        prop._super_set_mock.reset_mock()

        mock_notifier_instance = MagicMock(spec=Notifier)
        prop._get_notifier = MagicMock(return_value=mock_notifier_instance) # type: ignore[assignment]

        prop.__set__(instance, "new_value") # Calls ReactivePropertyMixin.__set__ -> _set

        prop._super_set_mock.assert_called_once_with(instance, "new_value")
        prop._get_notifier.assert_called_once_with(instance)
        mock_notifier_instance.fire.assert_called_once_with()

    @pytest.mark.asyncio
    async def test_watch_async_yields_current_and_new_values(self):
        # Mock fget for the property to return a dynamic value
        current_value = "initial_value"
        def mock_fget(inst: Any) -> str:
            return current_value

        prop = TestReactivePropertyMixin.PropWithMixin(fget=mock_fget)
        prop.__set_name__(MockOwner, "watched_prop") # Needed for TypedProperty fallback if fget is None
        instance = MockOwner()

        # Test `watch_async(instance)` Method:
        # - Test it yields the current value of the property immediately upon first `await anext()`.
        # - Test it yields new values when the property's notifier is fired (e.g., after `_set`).
        # - Test it correctly uses `notifier.event_context()` from `Notifier`.
        # - Test `event.clear()` is called in the loop.
        # - Test `asyncio.sleep(0)` is present (hard to test directly, assume from code review or side-effects).
        
        async_iter = prop.watch_async(instance)
        
        # Test initial value
        first_val = await asyncio.wait_for(anext(async_iter), timeout=1)
        assert first_val == "initial_value"

        # Test new value after change
        # This involves triggering the notifier. Direct __set__ on mixin might not use mock_fget for old value.
        # The _set method in ReactivePropertyMixin fires notifier AFTER super()._set.
        # Let's simulate the notifier firing directly for a cleaner test of watch_async reacting to it.
        
        notifier = prop._get_notifier(instance)
        
        # Change the value that mock_fget will return
        current_value = "updated_value_1"
        notifier.fire() # Simulate property change notification
        
        # Check for updated value
        # Need a small delay for the event loop to process the event set by fire()
        # and for watch_async to pick it up.
        try:
            updated_val = await asyncio.wait_for(anext(async_iter), timeout=0.1)
            assert updated_val == "updated_value_1"
        except asyncio.TimeoutError:
            pytest.fail("watch_async did not yield updated value in time")

        # Test another update
        current_value = "updated_value_2"
        notifier.fire()
        try:
            updated_val_2 = await asyncio.wait_for(anext(async_iter), timeout=0.1)
            assert updated_val_2 == "updated_value_2"
        except asyncio.TimeoutError:
            pytest.fail("watch_async did not yield second updated value in time")

        # How to test event.clear() and asyncio.sleep(0)?
        # - event.clear(): After a value is yielded, the internal event should be cleared.
        #   If we fire notifier again, it should set the event again.
        #   This is implicitly tested by the multiple updates working.
        # - asyncio.sleep(0): Ensures other tasks can run. Hard to assert directly in test.
        #   Relies on code structure.

    @pytest.mark.asyncio
    async def test_watch_async_multiple_observers(self):
        current_value = "start"
        def mock_fget(inst: Any) -> str: return current_value
        prop = TestReactivePropertyMixin.PropWithMixin(fget=mock_fget)
        instance = MockOwner()

        observer1_values = []
        observer2_values = []

        async def observer_task(iterator, value_list):
            async for value in iterator:
                value_list.append(value)
                if len(value_list) == 2: # Limit to avoid test hanging indefinitely
                    break
        
        iter1 = prop.watch_async(instance)
        iter2 = prop.watch_async(instance)

        task1 = asyncio.create_task(observer_task(iter1, observer1_values))
        task2 = asyncio.create_task(observer_task(iter2, observer2_values))

        await asyncio.sleep(0.01) # Allow initial values to be processed

        current_value = "end"
        prop._get_notifier(instance).fire()

        await asyncio.wait_for(asyncio.gather(task1, task2), timeout=1)

        assert observer1_values == ["start", "end"]
        assert observer2_values == ["start", "end"]

# Remove the old placeholder for TestReactiveProperty if it exists
# And add the new TestReactiveProperty class

from rxprop.reactive_property import reactive_property # Import the decorator

class TestReactiveProperty:
    def test_instantiation_with_decorator(self):
        @reactive_property
        def fget_func(inst: Any) -> str:
            return "value_from_fget"
        
        assert isinstance(fget_func, ReactiveProperty), "Decorator should return a ReactiveProperty instance"
        # Check if fget is correctly assigned
        # The fget_func itself becomes the fref, and ReactiveProperty sets self.fget via GetterMixin
        # This might require an instance to test __get__ or direct inspection if possible
        assert fget_func.fget is fget_func # type: ignore[attr-defined] # fget is on GetterMixin
        assert fget_func.fref is fget_func # fref is on TypedProperty

    def test_inheritance(self):
        @reactive_property
        def my_prop(inst: Any) -> int:
            return 123
        
        assert isinstance(my_prop, GetterMixin)
        assert isinstance(my_prop, SetterMixin) # ReactiveProperty includes SetterMixin by default
        assert isinstance(my_prop, ReactivePropertyMixin)

    def test_get_functionality(self):
        mock_getter_impl = MagicMock(return_value="gotten_value")
        
        @reactive_property
        def prop_to_get(inst: Any) -> str:
            return mock_getter_impl(inst)

        class Owner:
            val: str = prop_to_get # type: ignore[assignment]

        owner_instance = Owner()
        
        # Test dependency registration (via ReactivePropertyMixin._get)
        buffer: set[Notifier] = set()
        with listen_for_dependencies(buffer):
            retrieved_value = owner_instance.val # Access the property
        
        assert retrieved_value == "gotten_value"
        mock_getter_impl.assert_called_once_with(owner_instance)
        assert len(buffer) == 1, "Dependency should have been registered"
        # The notifier for prop_to_get on owner_instance should be in buffer
        # prop_to_get is descriptor, prop_to_get._get_notifier(owner_instance) is the notifier
        assert prop_to_get._get_notifier(owner_instance) in buffer # type: ignore[attr-defined]

    def test_set_functionality(self):
        mock_setter_impl = MagicMock()

        @reactive_property
        def prop_to_set(inst: Any) -> str:
            return "placeholder_get" # Getter is still needed

        @prop_to_set.setter # type: ignore[attr-defined]
        def prop_to_set(inst: Any, value: str) -> None:
            mock_setter_impl(inst, value)

        class Owner:
            val: str = prop_to_set # type: ignore[assignment]

        owner_instance = Owner()
        prop_descriptor = Owner.val # This is actually the descriptor itself if accessed from class
                                  # For instance access: prop_descriptor = ReactiveProperty.get_instance_descriptor(Owner, 'val') or similar
        # We want to test the instance's notifier
        prop_notifier_mock = MagicMock(spec=Notifier)
        
        # Need to mock _get_notifier on the descriptor instance (prop_to_set)
        # as ReactivePropertyMixin._set will call self._get_notifier(instance).fire()
        original_get_notifier = prop_to_set._get_notifier # type: ignore[attr-defined]
        prop_to_set._get_notifier = MagicMock(return_value=prop_notifier_mock) # type: ignore[attr-defined, assignment]

        owner_instance.val = "new_set_value" # Set the property

        mock_setter_impl.assert_called_once_with(owner_instance, "new_set_value")
        prop_to_set._get_notifier.assert_called_once_with(owner_instance) # type: ignore[attr-defined]
        prop_notifier_mock.fire.assert_called_once_with()
        
        # Restore original method
        prop_to_set._get_notifier = original_get_notifier # type: ignore[attr-defined, assignment]

    @pytest.mark.asyncio
    async def test_change_notification_via_watch_async(self):
        class Owner:
            _internal_val: int = 0
            @reactive_property
            def my_prop(self) -> int:
                return self._internal_val
            
            @my_prop.setter # type: ignore[attr-defined]
            def my_prop(self, value: int) -> None:
                self._internal_val = value
        
        instance = Owner()
        async_iter = instance.my_prop.watch_async(instance) # Watch the property on the instance

        values_received = []
        async def collector():
            async for val in async_iter:
                values_received.append(val)
                if len(values_received) >= 3: # Expect initial + 2 changes
                    break
        
        collect_task = asyncio.create_task(collector())
        
        await asyncio.sleep(0.01) # Ensure collector starts and gets initial value

        instance.my_prop = 10
        await asyncio.sleep(0.01)
        
        instance.my_prop = 20
        await asyncio.sleep(0.01)

        await asyncio.wait_for(collect_task, timeout=1)

        assert values_received == [0, 10, 20]

# Ensure the old placeholder comments are removed.
# ... existing code ... 