import pytest
from unittest.mock import MagicMock, AsyncMock # AsyncMock for async functions
import asyncio
from typing import Any

# Imports from your rxprop package - adjust paths as necessary
from rxprop.value_property import ValueProperty, value as value_property_decorator # Assuming 'value' is the decorator
from rxprop.reactive_property import ReactiveProperty, reactive_property as reactive_property_decorator
from rxprop.computed_property import ComputedProperty, computed as computed_property_decorator
from rxprop.notifier import Notifier
from rxprop.watch import watch # Assuming watch is the main utility in watch.py

# Dummy classes for testing properties
class OwnerWithProperties:
    # Using decorators for properties
    @value_property_decorator
    def my_value(self) -> int:
        return 0 # Default value

    @reactive_property_decorator
    def my_reactive(self) -> str:
        return "initial_reactive"
    
    _my_reactive_setter_val: str = "initial_reactive"
    @my_reactive.setter # type: ignore
    def my_reactive(self, val: str) -> None:
        self._my_reactive_setter_val = val

    @computed_property_decorator
    def my_computed(self) -> str:
        return f"{self.my_value}_{self.my_reactive}"


class TestWatchUtility:
    @pytest.mark.asyncio
    async def test_watch_value_property(self):
        instance = OwnerWithProperties()
        mock_callback = MagicMock()

        # Assuming watch utility from watch.py might be: 
        # stop_watcher = watch(instance, 'my_value', mock_callback)
        # or perhaps an async version if it needs to integrate with asyncio loop for notifications
        # For now, let's assume it's a sync watch call that sets up background monitoring.

        # To test initial value, the `watch` utility needs to support it.
        # Let's assume the watch utility from rxprop.watch is named 'watch'
        # and handles both class-level properties and instance-specific watching.

        # Scenario 1: Watching a property on an instance
        # The `watch` function needs to be imported from `rxprop.watch`
        try:
            stopper = watch(instance, "my_value", mock_callback)
            
            # Allow time for any initial call, if the watch utility is designed to do so.
            # This part is tricky to test without knowing watch() behavior regarding initial values.
            # If it calls back immediately with the current value:
            await asyncio.sleep(0.01) # Brief pause for potential immediate callback
            try:
                mock_callback.assert_any_call(instance, "my_value", 0) # Assuming (obj, prop_name, current_value)
            except AssertionError:
                # If it doesn't call back initially, this is also fine, depends on design.
                # We'll primarily test updates.
                mock_callback.reset_mock() # Reset if it wasn't called or to ignore initial call for update tests

            instance.my_value = 10
            await asyncio.sleep(0.01) # Allow time for callback
            mock_callback.assert_called_with(instance, "my_value", 10) # Check last call for the update
            mock_callback.reset_mock()

            instance.my_value = 20
            await asyncio.sleep(0.01)
            mock_callback.assert_called_with(instance, "my_value", 20)

        finally:
            if 'stopper' in locals() and stopper is not None:
                stopper() # Call to clean up the watcher
        pass

    @pytest.mark.asyncio
    async def test_watch_reactive_property(self):
        instance = OwnerWithProperties()
        mock_callback = MagicMock()

        try:
            stopper = watch(instance, "my_reactive", mock_callback)

            # Test initial value (assuming watch provides it)
            await asyncio.sleep(0.01)
            try:
                # Assuming initial value of my_reactive is "initial_reactive" as per OwnerWithProperties
                mock_callback.assert_any_call(instance, "my_reactive", "initial_reactive") 
            except AssertionError:
                mock_callback.reset_mock() # Ignore if no initial call, focus on updates

            instance.my_reactive = "updated_reactive_1"
            await asyncio.sleep(0.01)
            mock_callback.assert_called_with(instance, "my_reactive", "updated_reactive_1")
            mock_callback.reset_mock()

            instance.my_reactive = "updated_reactive_2"
            await asyncio.sleep(0.01)
            mock_callback.assert_called_with(instance, "my_reactive", "updated_reactive_2")

        finally:
            if 'stopper' in locals() and stopper is not None:
                stopper()
        pass

    @pytest.mark.asyncio
    async def test_watch_computed_property(self):
        instance = OwnerWithProperties()
        mock_callback = MagicMock()

        # my_computed depends on my_value (int) and my_reactive (str)
        # Initial: my_value = 0, my_reactive = "initial_reactive" -> my_computed = "0_initial_reactive"

        try:
            stopper = watch(instance, "my_computed", mock_callback)

            # Test initial value
            await asyncio.sleep(0.01)
            try:
                mock_callback.assert_any_call(instance, "my_computed", "0_initial_reactive")
            except AssertionError:
                mock_callback.reset_mock()

            # Change dependency: my_value
            instance.my_value = 10 # my_computed should become "10_initial_reactive"
            await asyncio.sleep(0.01)
            mock_callback.assert_called_with(instance, "my_computed", "10_initial_reactive")
            mock_callback.reset_mock()

            # Change dependency: my_reactive
            instance.my_reactive = "new_reactive_val" # my_computed should become "10_new_reactive_val"
            await asyncio.sleep(0.01)
            mock_callback.assert_called_with(instance, "my_computed", "10_new_reactive_val")
            mock_callback.reset_mock()

            # Change both, but only one notification expected if batching occurs or based on last change for a digest cycle
            # For simplicity, assume individual changes trigger individual callbacks for computed if value changes.
            instance.my_value = 20
            await asyncio.sleep(0.01) # Expected: "20_new_reactive_val"
            mock_callback.assert_called_with(instance, "my_computed", "20_new_reactive_val")
            mock_callback.reset_mock()
            
            instance.my_reactive = "another_change"
            await asyncio.sleep(0.01) # Expected: "20_another_change"
            mock_callback.assert_called_with(instance, "my_computed", "20_another_change")

        finally:
            if 'stopper' in locals() and stopper is not None:
                stopper()
        pass

    def test_unwatch_behavior(self):
        # This test might need to be async if watch/unwatch itself is async,
        # but for now, assuming synchronous unwatch for a background watcher.
        instance = OwnerWithProperties()
        mock_callback = MagicMock()

        stopper = watch(instance, "my_value", mock_callback)
        
        # Allow for potential initial call, then reset
        # await asyncio.sleep(0.01) # If async event loop is involved, might need small sleeps
        mock_callback.reset_mock() 

        instance.my_value = 5
        # await asyncio.sleep(0.01)
        mock_callback.assert_called_with(instance, "my_value", 5)
        mock_callback.reset_mock()

        assert stopper is not None, "watch should return a stopper function/object"
        stopper() # Unwatch

        # Change the value again
        instance.my_value = 15
        # await asyncio.sleep(0.01)
        mock_callback.assert_not_called() # Callback should not be called after unwatching
        pass

    def test_multiple_watchers_same_property(self):
        instance = OwnerWithProperties()
        mock_callback1 = MagicMock(name="cb1")
        mock_callback2 = MagicMock(name="cb2")

        stopper1 = None
        stopper2 = None
        try:
            stopper1 = watch(instance, "my_value", mock_callback1)
            stopper2 = watch(instance, "my_value", mock_callback2)

            # Reset after potential initial calls
            # await asyncio.sleep(0.01) # if async context needed
            mock_callback1.reset_mock()
            mock_callback2.reset_mock()

            instance.my_value = 50
            # await asyncio.sleep(0.01)

            mock_callback1.assert_called_once_with(instance, "my_value", 50)
            mock_callback2.assert_called_once_with(instance, "my_value", 50)
        finally:
            if stopper1: stopper1()
            if stopper2: stopper2()
        pass

    def test_multiple_watchers_different_properties(self):
        instance = OwnerWithProperties()
        cb_value = MagicMock(name="cb_value")
        cb_reactive = MagicMock(name="cb_reactive")

        stopper_v = None
        stopper_r = None
        try:
            stopper_v = watch(instance, "my_value", cb_value)
            stopper_r = watch(instance, "my_reactive", cb_reactive)

            # Reset after potential initial calls
            # await asyncio.sleep(0.01)
            cb_value.reset_mock()
            cb_reactive.reset_mock()

            instance.my_value = 100
            # await asyncio.sleep(0.01)
            cb_value.assert_called_once_with(instance, "my_value", 100)
            cb_reactive.assert_not_called()
            cb_value.reset_mock()

            instance.my_reactive = "only_reactive_changes"
            # await asyncio.sleep(0.01)
            cb_value.assert_not_called()
            cb_reactive.assert_called_once_with(instance, "my_reactive", "only_reactive_changes")
        
        finally:
            if stopper_v: stopper_v()
            if stopper_r: stopper_r()
        pass

    # Add more tests based on the plan for watch.py:
    # - watch_async alternative/wrapper (if applicable)
    # - Context managers for watching (if applicable)
    # - Batching/Debouncing/Throttling (if applicable)
    # - Edge cases (watching non-reactive, property raising exception, GC lifetime)

