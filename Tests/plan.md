# Test Plan for `rxprop`

This plan outlines the tests for the `rxprop` package, which provides a reactive programming framework.

## 1. Core Property Functionality (`typed_property.py`)

Although `typed_property.py` is not directly exposed by `rxprop`, its components are fundamental.

### 1.1. `TypedProperty`
- **`test_typed_property_get_set_delete_name.py`** (Consider renaming or splitting if tests become too large)
    - Test basic instantiation (e.g., with and without `fref`).
    - Test `__get__` descriptor behavior:
        - Returns `self` when instance is `None`.
        - Calls `_get` for an instance, which by default raises `AttributeError`.
    - Test `__set__` descriptor behavior:
        - Calls `_set`, which by default raises `AttributeError`.
    - Test `__delete__` descriptor behavior:
        - Calls `_delete`, which by default raises `AttributeError`.
    - Test `__set_name__` correctly sets the `_name` attribute (e.g., from class assignment).
    - Test `__doc__` is inherited from `fref.__doc__` if `fref` is provided.
    - Test `_name` is initialized from `fref.__name__` if `fref` is provided.

### 1.2. Mixins
- **`test_getter_mixin.py`**
    - Test `GetterMixin` allows getting a value via a provided `fget` function.
    - Test `getter` decorator method correctly sets/updates `fget`.
    - Test `_get` falls back to `super()._get` if `fget` is `None`.
- **`test_setter_mixin.py`**
    - Test `SetterMixin` allows setting a value via a provided `fset` function.
    - Test `setter` decorator method correctly sets/updates `fset`.
    - Test `_set` falls back to `super()._set` if `fset` is `None`.
- **`test_deleter_mixin.py`**
    - Test `DeleterMixin` allows deleting a value via a provided `fdel` function.
    - Test `deleter` decorator method correctly sets/updates `fdel`.
    - Test `_delete` falls back to `super()._delete` if `fdel` is `None`.
- **`test_default_mixin.py`**
    - Test `DefaultMixin` uses the provided `fdefault` callable (passed in `__init__`) to produce a default value when its `_get` is called (e.g., through `super()._get` from a subclass like `ValueStashMixin` if a value isn't present).
    - Test `default` decorator method works to set/change the `fdefault` callable.
    - Test `fdefault` is called with the instance as an argument.

## 2. Notification System (`notifier.py`)

- **`test_notifier.py`** (or `test_events.py` - consider renaming to `test_notifier.py`)
    - **`Notifier` Class**:
        - Test `add_handler(handler)` correctly registers a handler.
        - Test `add_handler` supports adding the same handler multiple times (reference counting).
        - Test `fire()` calls all registered handlers.
        - Test `remove_handler(handler)` correctly unregisters a handler.
        - Test `remove_handler` respects reference counting (handler only fully removed when count is zero).
        - Test `fire()` does not call removed handlers.
        - Test `WeakKeyDictionary` behavior for `_handlers` (handlers are removed if the handler object is garbage collected - may be hard to test deterministically, but acknowledge its use).
        - **`handler_context(handler)`**:
            - Test handler is active (receives `fire()` calls) within the `with` block.
            - Test handler is inactive (does not receive `fire()` calls) after the `with` block exits normally.
            - Test handler is inactive after the `with` block exits due to an exception.
        - **`event_context()`**:
            - Test it yields an `asyncio.Event`.
            - Test the yielded event is set when the notifier's `fire()` method is called while the context is active.
            - Test the event is not set by `fire()` calls made after the context has exited.
            - Test multiple `event_context` instances on the same notifier.

## 3. Reactive Value (`value_property.py`)

- **`test_value_property.py`** (was `test_rx_value.py`)
    - **`ValueStashMixin`**:
        - Test `_get` retrieves a value from `_values` if the instance is a key.
        - Test `_get` calls `super()._get` if the instance is not in `_values` (e.g., to trigger default value generation from `DefaultMixin`).
        - Test `_set` stores the value in the `_values` `WeakKeyDictionary` for the instance.
        - Test `WeakKeyDictionary` behavior for `_values` (entry cleared when instance is GC'd - hard to test deterministically).
    - **`ValueProperty` Class & `value_property` Decorator** (was `ReactiveValue` & `rx_value`):
        - Test instantiation with `value_property(fdefault_func)`:
            - `ValueProperty` is created with `fdefault=fdefault_func` and `fref=fdefault_func`.
        - Test default value generation:
            - When a `ValueProperty` is first accessed on an instance, `fdefault_func` (from `DefaultMixin`) is called via `ValueStashMixin`'s fallback `_get`.
            - The result of `fdefault_func` is returned and should ideally be stashed by `ValueStashMixin` if it were to implement caching on default value resolution (or ensure `ValueProperty._get` handles this through its inheritance).
        - Test getting the value (exercises `ValueStashMixin._get`, `DefaultMixin` if not set).
        - Test setting the value (`ValueProperty._set` behavior):
            - It retrieves the current value using `self._get(instance)`.
            - If the new value is different from this current value:
                - It calls `super()._set(instance, value)` (which could be `ReactivePropertyMixin._set` or a base property set).
                - This `super()._set` call is then responsible for actually updating the stored value (e.g., via `ValueStashMixin._set` further down the MRO) and for triggering notifications if applicable.
            - If the new value is the same as the current value (obtained via `self._get`), `super()._set` is *not* called, thus skipping the underlying storage update and the notification.
        - Test `default()` method (from `DefaultMixin`) allows changing the `fdefault` factory, and this new factory is used for subsequent default value generations.
        - Test change notification via `watch_async` (if inherited, e.g. from `ReactivePropertyMixin`) when the value is set to a new, different value.
        - Test that different instances of a class using `value_property` have independent values and default value computations.

## 4. Reactive Property System (`reactive_property.py`)

- **`test_reactive_property.py`** (was `test_rx_property.py`)
    - **`listen_for_dependencies` Context Manager**:
        - Test that notifiers of properties accessed (via their `_get` method which calls `ReactivePropertyMixin._get`) within its scope are added to the provided `buffer` set.
        - Test `_dep_ctx_stack` is correctly managed (pushed on enter, popped on exit, even with exceptions).
        - Test behavior with nested `listen_for_dependencies` contexts (dependencies go to the innermost active context's buffer).
    - **`ReactivePropertyMixin`**:
        - Test `_get_notifier(instance)`:
            - Creates a new `Notifier` for an instance if one doesn't exist in `_notifiers`.
            - Returns the cached `Notifier` on subsequent calls for the same instance.
            - Uses `WeakKeyDictionary` for `_notifiers`.
        - Test `_get(instance, owner)`:
            - If `_dep_ctx_stack` is active, adds the instance's notifier (from `_get_notifier`) to the current dependency context buffer (`_dep_ctx_stack[-1]`).
            - Calls `super()._get(instance, owner)` to retrieve the actual value.
        - Test `_set(instance, value)`:
            - Calls `super()._set(instance, value)` to store the actual value.
            - Fires the instance's notifier via `_get_notifier(instance).fire()`.
        - **`watch_async(instance)` Method**:
            - Test it yields the current value of the property immediately upon first `await anext()`.
            - Test it yields new values when the property's notifier is fired (e.g., after `_set`).
            - Test it correctly uses `notifier.event_context()` from `Notifier` (i.e., awaits the event, then fetches new value).
            - Test `event.clear()` is called in the loop.
            - Test `asyncio.sleep(0)` is present.
            - Test multiple concurrent `watch_async` iterators on the same property instance receive updates.
    - **`ReactiveProperty` Class & `reactive_property` Decorator** (was `rx_property`):
        - Test instantiation with `reactive_property(fget_func)` decorator:
            - `ReactiveProperty` is created with `fget=fget_func` and `fref=fget_func`.
        - Test it correctly inherits from `GetterMixin`, `SetterMixin`, and `ReactivePropertyMixin`.
        - Test basic get functionality:
            - Delegates to `fget_func` (via `GetterMixin`).
            - Triggers dependency registration via `ReactivePropertyMixin._get`.
        - Test basic set functionality (after decorating setter with `@name.setter`):
            - Delegates to the `fset_func` (via `SetterMixin`).
            - Triggers notification via `ReactivePropertyMixin._set`.
        - Test change notification through `watch_async` when the property is set.

## 5. Computed Property (`computed_property.py`)

- **`test_computed_property.py`** (was `test_rx_computed.py`)
    - **`ComputedPropertyMixin` Functionality**:
        - Test `_get` calls the `_fcompute(instance)` function.
        - **Dependency Tracking within `_get`**:
            - Test `listen_for_dependencies` is used, and the `new_deps` set is populated with notifiers of reactive properties accessed during `_fcompute`.
            - Test identification of `added_deps = new_deps - old_deps` and `removed_deps = old_deps - new_deps`.
            - Test `self._get_notifier(instance).fire` is added as a handler to notifiers in `added_deps`.
            - Test `self._get_notifier(instance).fire` is removed as a handler from notifiers in `removed_deps`.
            - Test `self._deps` (`WeakKeyDictionary`) is updated to store `new_deps` for the instance.
            - Test lifecycle: no deps -> some deps -> different deps -> no deps.
            - Test `WeakKeyDictionary` behavior for `_deps`.
    - **`CachedPropertyMixin` Functionality**:
        - Test `_is_dirty(instance)`:
            - Returns `True` for a new instance or if `instance not in self._values`.
            - Lazily creates an `asyncio.Event` in `_dirty` (initially set) if not present for an instance.
            - On first call for an instance (or if event not yet linked), registers `_dirty[instance].set` as a handler to `self._get_notifier(instance)`.
            - Returns `self._dirty[instance].is_set()` status (or `True` if value not cached).
        - Test `_get(instance, owner)` behavior:
            - If `_is_dirty(instance)` is `False`, returns the cached value from `_values` without calling `super()._get` (no recomputation).
            - If `_is_dirty(instance)` is `True`, calls `value = super()._get(instance, owner)` to trigger recomputation (e.g., via `ComputedPropertyMixin._get`).
            - After recomputation (if dirty), the new value is stored in `_values[instance]`.
            - After recomputation (if dirty), `_dirty[instance].clear()` is called.
        - Test `WeakKeyDictionary` behavior for `_dirty` and `_values`.
    - **`ComputedProperty` Class & `computed_property` Decorator (Integration of Mixins)** (was `rx_computed`):
        - Test instantiation with `computed_property(fcompute_func)` decorator:
            - `ComputedProperty` is created with `fcompute=fcompute_func` and `fref=fcompute_func`.
        - Test initial `_get`: computes value (via `ComputedPropertyMixin`), caches it (via `CachedPropertyMixin`), and clears dirty flag.
        - Test subsequent `_get` when no dependencies have changed: returns cached value without recomputation.
        - **Re-computation Triggering and Value Propagation**:
            - Scenario: Dependency A's value changes.
                1. Dependency A's notifier fires.
                2. This calls the `ComputedProperty`'s notifier's `fire` method (handler added by `ComputedPropertyMixin`).
                3. The `ComputedProperty`'s notifier firing calls `_dirty[instance].set` (handler added by `CachedPropertyMixin`).
                4. A subsequent `_get` on `ComputedProperty` finds it dirty, recomputes (via `ComputedPropertyMixin`), updates `_values`, and clears `_dirty` flag.
        - **`watch_async(instance)` (inherited from `ReactivePropertyMixin` via `CachedPropertyMixin`)**:
            - Test it yields the initial computed value.
            - Test it yields new values when the computed value effectively changes. This means:
                - A dependency changes.
                - The computed property becomes dirty.
                - It is recomputed (e.g., on next `_get` or if `watch_async` itself triggers a `_get`).
                - The `ComputedProperty`'s own notifier is fired (due to the chain: dep change -> computed's handler -> computed's notifier fires -> `CachedPropertyMixin`'s handler sets dirty event. The actual `fire()` that `watch_async` listens to is the computed's own notifier, which should be fired by `ComputedPropertyMixin`'s `_get` *after* a successful re-evaluation if the value changed, or if its `_set` is ever directly called, though it's not designed for direct setting).
                *Clarification needed on when exactly the computed property's main notifier fires to update `watch_async`.* (The `ComputedPropertyMixin._get` itself doesn't fire its own notifier. `ReactivePropertyMixin._set` does. This implies `watch_async` on a plain computed might only update if its *dependencies* fire and it recomputes on the next `__get__` call *within* `watch_async`'s loop. This needs careful testing based on `ReactivePropertyMixin`'s `watch_async` implementation details.)

        - Test with no dependencies (value computed once, cached, never recomputed unless manually dirtied if possible).
        - Test with multiple dependencies.
        - Test with nested computed properties (e.g., `computed_A` depends on `computed_B` which depends on `value_C`).
        - Test behavior when `_fcompute` raises an exception:
            - Exception should propagate out of `_get`.
            - Cache (`_values`) should not be updated with a new value.
            - Dirty state (`_dirty` event) should ideally remain set or reflect the failed computation.

## 6. Watch Utilities (`watch.py`)

- **`test_watch.py`**
    - Test core functionality of utilities provided in `watch.py`.
    - **`watch` Function (if applicable)**:
        - Test watching a `value_property`:
            - Callback is called with initial value (if designed to do so).
            - Callback is called with new value upon change.
            - Test providing specific `instance` to watch.
        - Test watching a `reactive_property`:
            - Callback is called with initial value.
            - Callback is called with new value upon change.
        - Test watching a `computed_property`:
            - Callback is called with initial computed value.
            - Callback is called when the computed value changes due to dependency updates.
        - Test unwatching/stopping the watch.
        - Test behavior with multiple watchers on the same property.
        - Test behavior with watchers on multiple different properties.
        - Test interaction with `asyncio` event loop if it's an async watch.
    - **Context Managers for Watching (if applicable)**:
        - Test any context managers that simplify setting up and tearing down watchers.
    - **Batching/Debouncing/Throttling (if applicable)**:
        - If `watch.py` includes features for batching updates, debouncing, or throttling, test these mechanisms thoroughly.
    - Test edge cases:
        - Watching non-reactive attributes (should it error out or do nothing?).
        - Property raising an exception during get.
        - Lifetime management: ensure watchers are cleaned up if the watched object or watcher itself is garbage collected.

## 7. Integration and Edge Cases

- **`test_integration.py`**
    - Test interactions between `value_property`, `reactive_property` (with custom getter/setter), and `computed_property`.
        - e.g., `computed_property` depending on a `value_property` and a `reactive_property`.
        - e.g., an `reactive_property` whose getter/setter interact with other reactive components.
    - Test scenarios with multiple class instances, ensuring no interference between instance data (values, dependencies, notifiers).
    - Test behavior during garbage collection of instances holding reactive properties (verify `WeakKeyDictionary` dependent cleanup, though direct assertion is hard. Focus on ensuring no strong references prevent GC where not intended).
    - Test asynchronous scenarios:
        - Multiple updates to a property in quick succession before a `watch_async` consumer (or `watch.py` utility) processes them.
        - Multiple `watch_async` (or `watch.py` utility) observers on the same property and on different properties.
        - `computed_property` re-computation triggered by rapid changes in dependencies.
    - Test properties on classes with `__slots__` (if `WeakKeyDictionary` or other mechanisms rely on `__weakref__` which might be affected by `__slots__`).
    - Further explore the interaction of `watch_async` (and `watch.py` utilities) on a `computed_property`. When exactly does its notifier fire to update watchers? Is it after re-computation if the value changed, or only if explicitly fired? (This relates to the clarification point in section 5).

This plan should provide good coverage for the `rxprop` package. Test scripts should be created in the `Tests/rxprop/` directory, corresponding to the sections and files outlined above.
