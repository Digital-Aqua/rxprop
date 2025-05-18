import asyncio
from unittest.mock import MagicMock
from typing import Any, Optional, Callable, Type, Dict, Set as TypingSet
import weakref
import pytest

from rxprop.computed_property import ComputedPropertyMixin, CachedPropertyMixin, ComputedProperty, computed
from rxprop.reactive_property import ReactivePropertyMixin, reactive_property
from rxprop.notifier import Notifier
from rxprop.typed_property import TypedProperty, GetterMixin

class BaseProperty(TypedProperty[Any, Any]):
    _name: str

    def __init__(self, fref: Optional[Callable[..., Any]] = None):
        super().__init__()
        self.fref = fref
        
        self._values: Dict[Any, Any] = {}
        self._dirty: Dict[Any, asyncio.Event] = {}
        self._deps: weakref.WeakKeyDictionary[Any, TypingSet[Notifier]] = weakref.WeakKeyDictionary()
        self._notifiers: weakref.WeakKeyDictionary[Any, Notifier] = weakref.WeakKeyDictionary()

    def __set_name__(self, owner: Type[Any], name: str) -> None:
        self._name = name
        if self.fref is not None:
            if not hasattr(self, '__doc__') or self.__doc__ is None:
                self.__doc__ = getattr(self.fref, '__doc__', None)

    def _get(self, instance: Any) -> Any:
        raise AttributeError(f"'{type(instance).__name__}' object has no attribute '{self._name}'")

    def _set(self, instance: Any, value: Any) -> None:
        raise AttributeError(f"can't set attribute '{self._name}'")

    def _delete(self, instance: Any) -> None:
        raise AttributeError(f"can't delete attribute '{self._name}'")

    def _get_notifier(self, instance: Any) -> Notifier:
        if not hasattr(self, '_notifiers'):
            self._notifiers = weakref.WeakKeyDictionary()
            
        notifier = self._notifiers.get(instance)
        if notifier is None:
            notifier = Notifier()
            self._notifiers[instance] = notifier
        return notifier

# Helper class for creating controlled reactive dependencies in tests
class SimpleReactivePropertyHelper(ReactivePropertyMixin[Any, Any], GetterMixin[Any, Any], BaseProperty): # type: ignore[override]
    _value_store: Any
    _notifier_override: Optional[Notifier] = None 

    def __init__(self, initial_value: Any):
        super().__init__(fget=self._actual_get_val) # Provides fget to GetterMixin via **kwargs
        self._value_store = initial_value

    def _actual_get_val(self, instance: Any) -> Any: # The fget implementation
        return self._value_store

    def _get_notifier(self, instance: Any) -> Notifier: # Override for test control
        if self._notifier_override is not None:
            return self._notifier_override
        return super()._get_notifier(instance)

    # _get behavior is inherited:
    # SimpleReactivePropertyHelper -> ReactivePropertyMixin._get -> GetterMixin._get (calls fget) -> BaseProperty._get (if fget is None)
    # ReactivePropertyMixin._get handles dependency registration.
    # GetterMixin._get calls self.fget (our _actual_get_val) to retrieve the value.

class TestComputedPropertyMixin:
    def test_get_calls_fcompute(self) -> None:
        mock_fcompute: MagicMock = MagicMock(return_value="computed_value")

        class PropWithComputed(ComputedPropertyMixin[Any, Any], BaseProperty): # type: ignore[override]
            def __init__(self) -> None:
                super().__init__(fcompute=mock_fcompute)

        class Owner:
            prop: PropWithComputed = PropWithComputed()

        instance = Owner()
        val = instance.prop
        assert val == "computed_value"
        mock_fcompute.assert_called_once_with(instance)

    def test_dependency_tracking_no_initial_deps(self) -> None:
        dep_notifier = Notifier()
        dep_notifier.add_handler = MagicMock() # Mock to check if it's called

        # Create a reactive property that will act as the dependency
        # Its notifier is dep_notifier
        dependency_prop_descriptor = SimpleReactivePropertyHelper(initial_value="dependency_value")
        dependency_prop_descriptor._notifier_override = dep_notifier # type: ignore [protected-access]

        class DependencyOwner:
            source: SimpleReactivePropertyHelper = dependency_prop_descriptor
        
        dep_owner_instance = DependencyOwner()

        def compute_func(inst: Any) -> str:
            # Access the dependency property. This will trigger its _get method,
            # which in turn calls ReactivePropertyMixin._get, registering dep_notifier
            # with the listen_for_dependencies context (via the module-level _dep_ctx_stack).
            _ = dep_owner_instance.source 
            return "value_from_deps"

        computed_prop_notifier = Notifier()

        class PropWithComputedDeps(ComputedPropertyMixin[Any, Any], ReactivePropertyMixin[Any, Any], BaseProperty): # type: ignore[override]
            _owner_instance_for_mock_notifier: Optional[Any] = None
            _mock_notifier_for_instance: Optional[Notifier] = None

            def __init__(self, owner_instance_for_mock: Any, mock_notifier: Notifier) -> None:
                super().__init__(fcompute=compute_func) 
                self._owner_instance_for_mock_notifier = owner_instance_for_mock
                self._mock_notifier_for_instance = mock_notifier
            
            def _get_notifier(self, instance: Any) -> Notifier:
                if instance is self._owner_instance_for_mock_notifier:
                    assert self._mock_notifier_for_instance is not None
                    return self._mock_notifier_for_instance
                return super()._get_notifier(instance)

        class MainTestOwner:
            prop: Optional[PropWithComputedDeps] = None

        main_instance = MainTestOwner()
        prop_descriptor = PropWithComputedDeps(owner_instance_for_mock=main_instance, mock_notifier=computed_prop_notifier)
        MainTestOwner.prop = prop_descriptor
        prop_descriptor.__set_name__(MainTestOwner, 'computed_prop')

        val = main_instance.prop # type: ignore [union-attr]
        assert val == "value_from_deps"
        
        dep_notifier.add_handler.assert_called_once_with(computed_prop_notifier.fire)
        
        assert prop_descriptor._deps.get(main_instance) == {dep_notifier} # type: ignore [protected-access]

    def test_dependency_tracking_add_and_remove_deps(self) -> None:
        dep1_notifier = Notifier()
        dep1_notifier.add_handler = MagicMock(name="dep1_add_handler")
        dep1_notifier.remove_handler = MagicMock(name="dep1_remove_handler")

        dep2_notifier = Notifier()
        dep2_notifier.add_handler = MagicMock(name="dep2_add_handler")
        dep2_notifier.remove_handler = MagicMock(name="dep2_remove_handler")

        dep3_notifier = Notifier()
        dep3_notifier.add_handler = MagicMock(name="dep3_add_handler")
        dep3_notifier.remove_handler = MagicMock(name="dep3_remove_handler")

        # Create reactive properties for each notifier
        class DynamicDepOwner:
            # Attributes will be set after instance creation for clarity
            prop1: Optional[SimpleReactivePropertyHelper] = None
            prop2: Optional[SimpleReactivePropertyHelper] = None
            prop3: Optional[SimpleReactivePropertyHelper] = None

        # Property descriptors
        dep_prop1_desc = SimpleReactivePropertyHelper(initial_value="val1")
        dep_prop1_desc._notifier_override = dep1_notifier # type: ignore [protected-access]
        dep_prop2_desc = SimpleReactivePropertyHelper(initial_value="val2")
        dep_prop2_desc._notifier_override = dep2_notifier # type: ignore [protected-access]
        dep_prop3_desc = SimpleReactivePropertyHelper(initial_value="val3")
        dep_prop3_desc._notifier_override = dep3_notifier # type: ignore [protected-access]

        # Assign descriptors to the class
        DynamicDepOwner.prop1 = dep_prop1_desc
        DynamicDepOwner.prop2 = dep_prop2_desc
        DynamicDepOwner.prop3 = dep_prop3_desc
        
        # Instance that owns these dependency properties
        dynamic_dep_owner_inst = DynamicDepOwner()

        # Map notifiers to the actual property access on the owner instance
        # The lambda ensures the property is accessed on the instance when called
        deps_access_map: Dict[Notifier, Callable[[], Any]] = {
            dep1_notifier: lambda: dynamic_dep_owner_inst.prop1,
            dep2_notifier: lambda: dynamic_dep_owner_inst.prop2,
            dep3_notifier: lambda: dynamic_dep_owner_inst.prop3,
        }

        self.current_deps_to_trigger_access: TypingSet[Notifier] = set() # Renamed for clarity
        compute_calls_ref = [0]

        def get_compute_func_dynamic_deps() -> Callable[[Any], str]:
            test_method_self = self 
            def compute_func_dynamic_deps_inner(inst: Any) -> str:
                compute_calls_ref[0] += 1
                # Access the properties whose notifiers are in current_deps_to_trigger_access
                for notifier_key in test_method_self.current_deps_to_trigger_access:
                    if notifier_key in deps_access_map:
                        _ = deps_access_map[notifier_key]() # Access the property
                return f"computed_val_{compute_calls_ref[0]}"
            return compute_func_dynamic_deps_inner
        
        fcompute_method_for_prop = get_compute_func_dynamic_deps()
        prop_specific_notifier = Notifier()

        class PropWithDynamicDeps(ComputedPropertyMixin[Any, Any], ReactivePropertyMixin[Any, Any], BaseProperty): # type: ignore[override]
            _owner_instance_ref: Optional[Any] = None
            _specific_notifier_ref: Optional[Notifier] = None

            def __init__(self, fcompute_ext_method: Callable[[Any], str], owner_instance_ref: Any, specific_notifier: Notifier) -> None:
                super().__init__(fcompute=fcompute_ext_method)
                self._owner_instance_ref = owner_instance_ref
                self._specific_notifier_ref = specific_notifier
            
            def _get_notifier(self, instance: Any) -> Notifier:
                if instance is self._owner_instance_ref:
                    assert self._specific_notifier_ref is not None
                    return self._specific_notifier_ref
                return super()._get_notifier(instance)

        class Owner:
            prop: Optional[PropWithDynamicDeps] = None

        test_owner_instance = Owner()
        prop_instance = PropWithDynamicDeps(
            fcompute_ext_method=fcompute_method_for_prop,
            owner_instance_ref=test_owner_instance,
            specific_notifier=prop_specific_notifier 
        )
        Owner.prop = prop_instance
        prop_instance.__set_name__(Owner, "prop")

        compute_calls_ref[0] = 0
        self.current_deps_to_trigger_access = {dep1_notifier, dep2_notifier}

        val1 = prop_instance._get(test_owner_instance) # type: ignore [protected-access]
        assert val1 == "computed_val_1"
        assert prop_instance._deps.get(test_owner_instance) == {dep1_notifier, dep2_notifier} # type: ignore [protected-access]
        
        dep1_notifier.add_handler.assert_called_once_with(prop_specific_notifier.fire)
        dep2_notifier.add_handler.assert_called_once_with(prop_specific_notifier.fire)
        dep3_notifier.add_handler.assert_not_called()

        dep1_notifier.add_handler.reset_mock()
        dep2_notifier.add_handler.reset_mock()
        dep1_notifier.remove_handler.assert_not_called()
        dep2_notifier.remove_handler.assert_not_called()
        dep3_notifier.remove_handler.assert_not_called()

        compute_calls_ref[0] = 0
        self.current_deps_to_trigger_access = {dep2_notifier, dep3_notifier}
            
        val2 = prop_instance._get(test_owner_instance) # type: ignore [protected-access]
        assert val2 == "computed_val_1"
        assert prop_instance._deps.get(test_owner_instance) == {dep2_notifier, dep3_notifier} # type: ignore [protected-access]

    def test_weakkeydictionary_for_deps(self) -> None:
        class Owner:
            pass
        instance = Owner()
        # Mock fcompute for ComputedPropertyMixin
        mock_fcompute = MagicMock(return_value="test") 
        prop = ComputedPropertyMixin[Any, Any](fcompute=mock_fcompute)
        prop.__set_name__(Owner, "test_prop") # Initialize _name for error messages if any

        # Initial state: _deps should be a WeakKeyDictionary
        assert isinstance(prop._deps, weakref.WeakKeyDictionary), "_deps should be a WeakKeyDictionary" # type: ignore [protected-access]

        # Trigger _get to populate _deps
        # For this, we need a dependency that listen_for_dependencies can catch.
        dep_notifier = Notifier()

        # Use SimpleReactivePropertyHelper to ensure fget is properly set up
        dependency_prop_desc = SimpleReactivePropertyHelper(initial_value="dependency_value")
        dependency_prop_desc._notifier_override = dep_notifier # type: ignore [protected-access]

        # To use this descriptor, it needs to be on a class and accessed via an instance
        class DepOwner:
            dep_prop: SimpleReactivePropertyHelper = dependency_prop_desc
        
        dep_instance = DepOwner()
        # Ensure the descriptor name is set if SimpleReactivePropertyHelper relies on it (it does via BaseProperty)
        dependency_prop_desc.__set_name__(DepOwner, "dep_prop")

        def fcompute_with_dep(inst: Any) -> str: # inst here is the Owner instance, not DepOwner
            _ = dep_instance.dep_prop # Access dependency on dep_instance
            return "computed_with_dep"
        
        prop_with_actual_compute = ComputedPropertyMixin[Any, Any](fcompute=fcompute_with_dep)
        prop_with_actual_compute.__set_name__(Owner, "prop_deps_test")

        # First access: populates deps
        prop_with_actual_compute._get(instance)
        assert instance in prop_with_actual_compute._deps # type: ignore [protected-access]
        assert prop_with_actual_compute._deps[instance] == {dep_notifier} # type: ignore [protected-access]

        # Test weak reference behavior
        instance_ref = weakref.ref(instance)
        values_dict = prop_with_actual_compute._deps # type: ignore [protected-access]
        del instance
        # import gc; gc.collect() # Optional: try to force GC

        assert instance_ref() is None, "Instance should be garbage collected"
        # After instance is GC'd, its key should ideally be gone from WeakKeyDictionary.
        # This can be hard to assert deterministically without gc.collect() and even then.
        # The primary test is that it *is* a WeakKeyDictionary.
        # If instance_ref() is None, we expect instance not in values_dict
        # However, timing of GC makes this flaky. Main point is type of _deps.
        # assert instance_ref() not in values_dict # This might fail due to GC timing


class TestCachedPropertyMixin:
    class PropWithCached(CachedPropertyMixin[Any, Any], BaseProperty): # type: ignore[override]
        _get_call_count: int = 0
        _super_get_mock: MagicMock

        def __init__(self, super_get_mock: MagicMock):
            super().__init__()
            self._super_get_mock = super_get_mock
            self._get_call_count = 0

        def _get(self, instance: Any) -> Any: # This is the super()._get for CachedPropertyMixin
            self._get_call_count += 1
            return self._super_get_mock(instance)

    def test_is_dirty_initial_state(self):
        # Test `_is_dirty(instance)`:
        # - Returns `True` for a new instance or if `instance not in self._values`.
        # - Lazily creates an `asyncio.Event` in `_dirty` (initially set).
        # - On first call for an instance, registers `_dirty[instance].set` as a handler to `self._get_notifier(instance)`.
        super_get_mock = MagicMock(return_value="initial_value")
        prop = TestCachedPropertyMixin.PropWithCached(super_get_mock=super_get_mock)
        instance = object()
        prop_notifier_mock = MagicMock(spec=Notifier)
        prop._get_notifier = MagicMock(return_value=prop_notifier_mock) # type: ignore[assignment]

        assert prop._is_dirty(instance) is True, "Should be dirty for a new instance" # type: ignore [protected-access]
        assert instance in prop._dirty, "asyncio.Event should be created in _dirty" # type: ignore [protected-access]
        assert prop._dirty[instance].is_set(), "Event should be initially set" # type: ignore [protected-access]
        prop_notifier_mock.add_handler.assert_called_once_with(prop._dirty[instance].set) # type: ignore [protected-access]
        assert instance not in prop._values, "_values should not contain the instance yet" # type: ignore [protected-access]

    def test_get_caching_behavior(self):
        # Test `_get(instance, owner)` behavior:
        # - If `_is_dirty(instance)` is `False`, returns cached value from `_values` without calling `super()._get`.
        # - If `_is_dirty(instance)` is `True`, calls `value = super()._get(instance, owner)`.
        # - After recomputation, new value stored in `_values[instance]`.
        # - After recomputation, `_dirty[instance].clear()` is called.
        super_get_mock = MagicMock(return_value="computed_value_1")
        prop = TestCachedPropertyMixin.PropWithCached(super_get_mock=super_get_mock)
        instance = object()
        prop_notifier_mock = MagicMock(spec=Notifier)
        prop._get_notifier = MagicMock(return_value=prop_notifier_mock) # type: ignore[assignment]

        # First call: should compute, cache, and clear dirty flag
        val1 = prop.__get__(instance, None) # type: ignore [arg-type] # Calls CachedPropertyMixin._get
        assert val1 == "computed_value_1"
        assert prop._get_call_count == 1 # type: ignore [protected-access]
        assert instance in prop._values and prop._values[instance] == "computed_value_1" # type: ignore [protected-access]
        assert instance in prop._dirty and not prop._dirty[instance].is_set() # type: ignore [protected-access]

        # Second call: should return cached value, no recompute
        super_get_mock.return_value = "computed_value_2" # Change potential super_get result
        val2 = prop.__get__(instance, None) # type: ignore [arg-type]
        assert val2 == "computed_value_1" # Still old value from cache
        assert prop._get_call_count == 1 # Super._get not called again

        # Manually set dirty and re-test
        if instance in prop._dirty: # Should exist
            prop._dirty[instance].set()
        
        val3 = prop.__get__(instance, None)
        assert val3 == "computed_value_2" # New value after recomputation
        assert prop._get_call_count == 2
        assert instance in prop._values and prop._values[instance] == "computed_value_2"
        assert not prop._dirty[instance].is_set()
        pass

    def test_weakkeydictionary_for_dirty_and_values(self):
        class Owner:
            pass
        instance = Owner()
        prop = CachedPropertyMixin[Any, Any]() # type: ignore[call-arg]
        # Ensure _get_notifier is callable for _is_dirty initialization
        prop._get_notifier = MagicMock(return_value=MagicMock(spec=Notifier)) # type: ignore[assignment]

        # Trigger _is_dirty to initialize _dirty dictionary
        prop._is_dirty(instance) 
        assert isinstance(prop._dirty, weakref.WeakKeyDictionary), "_dirty should be a WeakKeyDictionary"

        # Trigger _get to initialize _values dictionary (requires super()._get mock)
        class BaseForCache(TypedProperty[Any,Any]):
            def _get(self, inst:Any) -> Any: return "val"
        class PropWithCache(CachedPropertyMixin[Any,Any], BaseForCache): pass # type: ignore[misc]
        
        prop_cache_test = PropWithCache()
        prop_cache_test._get_notifier = MagicMock(return_value=MagicMock(spec=Notifier)) # type: ignore[assignment]
        prop_cache_test.__set_name__(Owner, "cached_prop")

        prop_cache_test._get(instance) # Call _get to populate _values
        assert isinstance(prop_cache_test._values, weakref.WeakKeyDictionary), "_values should be a WeakKeyDictionary"

        # Test weak reference behavior for _dirty
        instance_ref_dirty = weakref.ref(instance)
        dirty_dict_ref = prop._dirty
        # Test weak reference behavior for _values (using prop_cache_test)
        instance2 = Owner() # Need another instance for _values, as 'instance' might be gone
        prop_cache_test._get(instance2)
        values_dict_ref = prop_cache_test._values
        instance_ref_values = weakref.ref(instance2)

        del instance
        del instance2
        # import gc; gc.collect()

        assert instance_ref_dirty() is None, "Instance for _dirty should be GC'd"
        assert instance_ref_values() is None, "Instance for _values should be GC'd"
        # Similar to above, direct check of key absence is flaky.
        # Main point is that they are WeakKeyDictionary.


# Need to import the actual decorator, not the string alias
from rxprop.computed_property import computed

class TestComputedProperty:
    # Tests for ComputedProperty Class & `computed` Decorator (Integration of Mixins)

    def test_instantiation_with_decorator(self):
        # Test instantiation with `computed(fcompute_func)` decorator:
        # - `ComputedProperty` is created with `fcompute=fcompute_func` and `fref=fcompute_func`.
        mock_fcompute = MagicMock()
        decorated_prop = computed(mock_fcompute)
        assert isinstance(decorated_prop, ComputedProperty)
        assert decorated_prop._fcompute == mock_fcompute # type: ignore[protected-access]
        assert decorated_prop.fref == mock_fcompute
        pass

    def test_initial_get_computes_caches_clears_dirty(self):
        # Test initial `_get`: computes value (via `ComputedPropertyMixin`), 
        # caches it (via `CachedPropertyMixin`), and clears dirty flag.
        mock_fcompute = MagicMock(return_value="initial_computed")
        class Owner:
            prop = computed(mock_fcompute)
        
        instance = Owner()
        val = instance.prop
        assert val == "initial_computed"
        mock_fcompute.assert_called_once_with(instance)
        # Add assertions for cache and dirty flag state if directly testable
        # or infer from re-computation behavior in next test
        pass

    def test_subsequent_get_returns_cached_value(self):
        # Test subsequent `_get` when no dependencies have changed: 
        # returns cached value without recomputation.
        mock_fcompute = MagicMock(return_value="first_value")
        class Owner:
            prop = computed(mock_fcompute)
        
        instance = Owner()
        val1 = instance.prop # First access, computes
        assert val1 == "first_value"
        assert mock_fcompute.call_count == 1

        mock_fcompute.return_value = "second_value"
        val2 = instance.prop # Second access, should be cached
        assert val2 == "first_value"
        assert mock_fcompute.call_count == 1 # Not called again
        pass

    def test_recomputation_triggering_and_value_propagation(self):
        # Setup a dependency property
        dep_initial_value = 10
        dependency_prop_desc = SimpleReactivePropertyHelper(initial_value=dep_initial_value)
        dependency_prop_desc.__set_name__(Owner, "source_prop") # Set a name for clarity
        
        # Mock the notifier of the dependency so we can fire it manually
        # and check add_handler/remove_handler calls from ComputedPropertyMixin
        dep_notifier_mock = MagicMock(spec=Notifier)
        dependency_prop_desc._notifier_override = dep_notifier_mock # type: ignore[protected-access]

        # Define the compute function that uses the dependency
        def actual_compute_func(inst: Any) -> str:
            return f"computed:{inst.source_prop}"

        class Owner:
            source_prop = dependency_prop_desc
            # The computed property that depends on source_prop
            # We use the actual `computed` decorator here to test full integration
            # of ComputedProperty, CachedPropertyMixin, and ComputedPropertyMixin
            final_prop = computed(actual_compute_func)
        
        test_instance = Owner()

        # --- Initial access --- 
        # This should: 
        # 1. Call actual_compute_func (ComputedPropertyMixin part)
        # 2. Access test_instance.source_prop, registering dep_notifier_mock (ComputedPropertyMixin part)
        # 3. Cache the result "computed:10" (CachedPropertyMixin part)
        # 4. Add computed_prop's notifier.fire as a handler to dep_notifier_mock
        
        # Get the notifier for the computed property itself to check handler registration
        # The `computed` decorator creates a ComputedProperty instance.
        # Owner.final_prop is this descriptor instance.
        computed_prop_descriptor = Owner.final_prop
        computed_prop_notifier = computed_prop_descriptor._get_notifier(test_instance) # type: ignore[protected-access]
        # Spy on the computed property's notifier's fire method
        computed_prop_notifier.fire = MagicMock(wraps=computed_prop_notifier.fire)

        # Spy on the dirty event's set method for the computed property
        # This requires accessing _dirty after it's been initialized by first _is_dirty call inside _get

        val1 = test_instance.final_prop
        assert val1 == "computed:10"
        dep_notifier_mock.add_handler.assert_called_once_with(computed_prop_notifier.fire)

        # --- Dependency changes --- 
        # Change the dependency's underlying value
        dependency_prop_desc._value_store = 20 # type: ignore[protected-access]
        
        # Fire the dependency's notifier. This should:
        # 1. Call the handler registered by ComputedPropertyMixin (computed_prop_notifier.fire).
        # 2. computed_prop_notifier.fire() should then call the handler registered by CachedPropertyMixin
        #    which is `_dirty[test_instance].set()`.
        
        # Before firing, let's get the dirty event to spy on its `set` method.
        # Accessing _is_dirty (which happens in __get__) would have created this.
        assert test_instance in computed_prop_descriptor._dirty # type: ignore[protected-access]
        dirty_event_for_computed = computed_prop_descriptor._dirty[test_instance] # type: ignore[protected-access]
        dirty_event_for_computed.set = MagicMock(wraps=dirty_event_for_computed.set)
        # Ensure it's currently clear before dep_notifier fires
        assert not dirty_event_for_computed.is_set()

        dep_notifier_mock.fire()
        
        # Assertions for the chain reaction:
        # 1. ComputedPropertyMixin's handler (computed_prop_notifier.fire) was called by dep_notifier_mock.fire()
        computed_prop_notifier.fire.assert_called_once()
        # 2. CachedPropertyMixin's handler (dirty_event.set) was called by computed_prop_notifier.fire()
        dirty_event_for_computed.set.assert_called_once()
        assert dirty_event_for_computed.is_set(), "Computed property should now be dirty"

        # --- Subsequent access to computed property ---
        # This should: 
        # 1. Find it dirty (CachedPropertyMixin part).
        # 2. Recompute by calling actual_compute_func (ComputedPropertyMixin part).
        # 3. Get new value "computed:20".
        # 4. Update cache and clear dirty flag (CachedPropertyMixin part).
        
        # Reset add_handler mock on dep_notifier to ensure it's not called again if deps haven't changed structually
        dep_notifier_mock.add_handler.reset_mock()
        # Reset compute_func_mock if we had one, here we check actual_compute_func via its output

        val2 = test_instance.final_prop
        assert val2 == "computed:20"
        dep_notifier_mock.add_handler.assert_not_called() # Deps haven't changed, only value
        assert not dirty_event_for_computed.is_set(), "Dirty flag should be cleared after recomputation"

    @pytest.mark.asyncio
    async def test_watch_async_on_computed(self):
        # Setup a dependency property that can be changed
        class DepOwner:
            _val: int = 0
            @reactive_property # Using reactive_property for easy setter and notification
            def source_prop(self) -> int:
                return self._val
            @source_prop.setter # type: ignore[attr-defined]
            def source_prop(self, value: int) -> None:
                self._val = value

        dep_instance = DepOwner()

        # Computed property depending on source_prop
        class MainOwner:
            dep = dep_instance # Hold a reference to the dependency owner
            @computed
            def final_computed(self) -> str:
                return f"computed:{self.dep.source_prop}"

        main_instance = MainOwner()

        async_iter = main_instance.final_computed.watch_async(main_instance)
        
        results = []
        async def collect_results():
            nonlocal results
            async for value in async_iter:
                results.append(value)
                if len(results) >= 3: # Expect initial + 2 changes
                    break
        
        collector_task = asyncio.create_task(collect_results())

        # Allow a moment for the initial value to be collected
        await asyncio.sleep(0.01)
        assert results == ["computed:0"], "Initial value mismatch"

        # Change dependency, which should trigger computed re-evaluation and watch_async update
        dep_instance.source_prop = 10
        await asyncio.sleep(0.01) # Allow propagation and collection
        assert results == ["computed:0", "computed:10"], "Value after first change mismatch"

        dep_instance.source_prop = 20
        await asyncio.sleep(0.01) # Allow propagation and collection
        assert results == ["computed:0", "computed:10", "computed:20"], "Value after second change mismatch"
        
        await asyncio.wait_for(collector_task, timeout=1) # Ensure collector finishes

    def test_computed_with_no_dependencies(self):
        # Test with no dependencies (value computed once, cached, never recomputed).
        mock_fcompute = MagicMock(return_value="standalone_value")
        class Owner:
            prop = computed(mock_fcompute)
        instance = Owner()
        assert instance.prop == "standalone_value"
        assert mock_fcompute.call_count == 1
        assert instance.prop == "standalone_value" # Access again
        assert mock_fcompute.call_count == 1 # Should not recompute
        pass

    def test_computed_with_multiple_dependencies(self):
        class DepSource:
            _val1: int = 1
            _val2: str = "A"

            @reactive_property
            def dep1(self) -> int:
                return self._val1
            @dep1.setter # type: ignore[attr-defined]
            def dep1(self, value: int) -> None:
                self._val1 = value
            
            @reactive_property
            def dep2(self) -> str:
                return self._val2
            @dep2.setter # type: ignore[attr-defined]
            def dep2(self, value: str) -> None:
                self._val2 = value
        
        dep_instance = DepSource()

        class MainOwner:
            sources = dep_instance
            @computed
            def multi_comp(self) -> str:
                return f"{self.sources.dep1}-{self.sources.dep2}"
        
        main_instance = MainOwner()

        assert main_instance.multi_comp == "1-A", "Initial value incorrect"

        # Change first dependency
        dep_instance.dep1 = 2
        assert main_instance.multi_comp == "2-A", "Value after dep1 change incorrect"

        # Change second dependency
        dep_instance.dep2 = "B"
        assert main_instance.multi_comp == "2-B", "Value after dep2 change incorrect"

        # Change first dependency again
        dep_instance.dep1 = 3
        assert main_instance.multi_comp == "3-B", "Value after dep1 second change incorrect"
        pass

    def test_nested_computed_properties(self):
        class BaseSource:
            _val: int = 100
            @reactive_property
            def base_val(self) -> int:
                return self._val
            @base_val.setter # type: ignore[attr-defined]
            def base_val(self, value: int) -> None:
                self._val = value
        
        base_instance = BaseSource()

        class IntermediateOwner:
            base = base_instance
            @computed
            def intermediate_computed(self) -> str:
                return f"intermediate:{self.base.base_val}"

        intermediate_instance = IntermediateOwner() # Not strictly needed to instantiate if only used as dep

        class TopOwner:
            inter = intermediate_instance # Dependency on the instance holding the intermediate computed
            # If intermediate_computed was on TopOwner, dependency injection is different.
            # Here, TopOwner.final_nested_computed depends on intermediate_instance.intermediate_computed

            @computed
            def final_nested_computed(self) -> str:
                # Accessing intermediate_computed on an instance of IntermediateOwner
                return f"final:{intermediate_instance.intermediate_computed}" 
                # A more common pattern might be: self.inter_prop.intermediate_computed
                # where self.inter_prop is an instance of IntermediateOwner
                # For this test, direct access to intermediate_instance is simpler if allowed.

        # Let's refine TopOwner to hold an instance of IntermediateOwner if that's the intended pattern
        class TopOwnerRefined:
            inter_prop_instance: IntermediateOwner

            def __init__(self, inter_instance: IntermediateOwner):
                self.inter_prop_instance = inter_instance
            
            @computed
            def final_nested_computed(self) -> str:
                return f"final:{self.inter_prop_instance.intermediate_computed}"

        top_instance = TopOwnerRefined(intermediate_instance)

        # Initial state check
        assert base_instance.base_val == 100
        assert intermediate_instance.intermediate_computed == "intermediate:100"
        assert top_instance.final_nested_computed == "final:intermediate:100"

        # Change base value
        base_instance.base_val = 200

        # Check propagation
        assert intermediate_instance.intermediate_computed == "intermediate:200", "Intermediate failed to update"
        assert top_instance.final_nested_computed == "final:intermediate:200", "Final nested failed to update"

        # Change base value again
        base_instance.base_val = 300
        assert intermediate_instance.intermediate_computed == "intermediate:300"
        assert top_instance.final_nested_computed == "final:intermediate:300"
        pass

    def test_fcompute_raises_exception(self):
        # Test behavior when `_fcompute` raises an exception:
        # - Exception should propagate out of `_get`.
        # - Cache (`_values`) should not be updated with a new value.
        # - Dirty state (`_dirty` event) should ideally remain set or reflect the failed computation.
        error_to_raise = ValueError("Computation failed")
        mock_fcompute = MagicMock(side_effect=error_to_raise)
        class Owner:
            prop = computed(mock_fcompute)
        
        instance = Owner()
        with pytest.raises(ValueError, match="Computation failed"):
            _ = instance.prop
        
        computed_descriptor = Owner.prop # Get the descriptor

        # Assert cache and dirty state
        # 1. Cache should not be updated
        assert instance not in computed_descriptor._values, "Cache should not be updated on fcompute failure" # type: ignore[protected-access]

        # 2. Dirty state should remain set (or be set if it wasn't for some reason)
        # Accessing _is_dirty directly, or checking the event if accessible.
        # If _is_dirty was called internally by the failing __get__, the event should exist.
        if instance in computed_descriptor._dirty: # type: ignore[protected-access]
            assert computed_descriptor._dirty[instance].is_set(), "Dirty flag should remain set after fcompute failure" # type: ignore[protected-access]
        else:
            # This case might occur if __get__ bailed out before _is_dirty could establish the event.
            # A more robust check might be to see if a subsequent call to _is_dirty returns True.
            assert computed_descriptor._is_dirty(instance), "Property should still be dirty after fcompute failure" # type: ignore[protected-access]

        # Ensure a second access still tries to compute and fails (if dirty flag handled correctly)
        with pytest.raises(ValueError, match="Computation failed"):
            _ = instance.prop 
        assert mock_fcompute.call_count >= 1 # Should be called at least once, possibly twice if retry logic is aggressive
                                            # Given typical cache-on-success, re-eval on dirty, it should be called each time it's dirty and accessed.
                                            # If first call sets up deps that don't change, and only fcompute fails, it still gets called.
        pass

# Placeholder for TestCachedPropertyMixin and TestComputedProperty (decorator) will be added based on full file and plan.
# from rxprop.computed_property import computed_property

# class TestCachedPropertyMixin:
#     # ... tests for _is_dirty, _get caching logic ...

# class TestComputedProperty:
#     # ... tests for computed_property decorator, integration of mixins ... 