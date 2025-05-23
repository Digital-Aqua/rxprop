# Test Plan for `rxprop` Package

This document outlines the test plan for the `rxprop` package, focusing on its core reactive programming functionalities.

## 1. Key Behaviours

The `rxprop` package provides mechanisms for creating and managing reactive properties. Key behaviors include:

*   **Value Properties (`@rxprop.value`)**:
    *   Storing and retrieving a value.
    *   Lazy initialization of default values.
    *   Notifying watchers when the value changes.
*   **Computed Properties (`@rxprop.computed`)**:
    *   Calculating a value based on a function.
    *   Automatically tracking dependencies (other reactive properties).
    *   Re-calculating and notifying watchers when dependencies change.
    *   Caching computed values and only recomputing when dirty.
*   **Reactive Properties (`@rxprop.reactive_property`)**:
    *   General-purpose reactive properties with custom getters/setters.
    *   Notifying watchers on change.
*   **Watchers (`rxprop.watch`)**:
    *   Asynchronously observing changes to reactive properties.
    *   Receiving updated values when a watched property changes.
*   **Notifier (`rxprop.notifier.Notifier`)**:
    *   Core mechanism for signaling changes.
    *   Adding and removing handlers.
    *   Firing events to trigger handlers.
    *   Providing an `asyncio.Event` context for asynchronous waiting.
*   **Dependency Tracking (`listen_for_dependencies`)**:
    *   Correctly identifying and registering properties accessed within a computation.
*   **Typed Properties (`TypedProperty`, `GetterMixin`, `SetterMixin`, etc.)**:
    *   Ensuring properties can be defined with type safety.
    *   Correct functioning of `__get__`, `__set__`, `__delete__`, `__set_name__`.
    *   Correct application of getter, setter, deleter, and default value factory mixins.

---

## 2. Scenarios

### 2.1 `rxprop.value`

#### 2.1.1 Basic Value Storage and Retrieval
*   **Given** a class with an `rxprop.value` property
    *   **When** an instance of the class is created
    *   **Then** the property can be accessed and returns its default value (if defined via decorated function).
*   **Given** an `rxprop.value` property on an instance
    *   **When** a new value is assigned to the property
    *   **Then** the property stores the new value.
*   **Given** an `rxprop.value` property on an instance
    *   **When** the property is accessed multiple times without change
    *   **Then** it consistently returns the same stored value.

#### 2.1.2 Default Value Initialization
*   **Given** an `rxprop.value` property with a default value factory function
    *   **When** the property is first accessed
    *   **Then** the default value factory function is called exactly once.
*   **Given** an `rxprop.value` property with a default value factory function
    *   **When** the property is set before its first access
    *   **Then** the default value factory function is NOT called.

#### 2.1.3 Notification on Change
*   **Given** an `rxprop.value` property and an active watcher on it
    *   **When** the property's value is set to a new, different value
    *   **Then** the watcher is notified with the new value.
*   **Given** an `rxprop.value` property and an active watcher on it
    *   **When** the property's value is set to the same value it currently holds
    *   **Then** the watcher is NOT notified (implementation detail to confirm, but typical reactive behavior).

---

### 2.2 `rxprop.computed`

#### 2.2.1 Basic Computation
*   **Given** a class with an `rxprop.computed` property that depends on one or more `rxprop.value` properties
    *   **When** an instance is created
    *   **Then** the computed property returns the correctly calculated value based on the initial values of its dependencies.

#### 2.2.2 Dependency Tracking and Re-computation
*   **Given** a `rxprop.computed` property and its `rxprop.value` dependency
    *   **When** the dependency's value changes
    *   **Then** the computed property's value is re-calculated and updated.
*   **Given** a `rxprop.computed` property with multiple `rxprop.value` dependencies
    *   **When** any of its dependencies change
    *   **Then** the computed property is re-calculated.
*   **Given** a `rxprop.computed` property
    *   **When** a non-dependency reactive property changes
    *   **Then** the computed property is NOT re-calculated.

#### 2.2.3 Caching
*   **Given** a `rxprop.computed` property
    *   **When** the property is accessed multiple times without any change in its dependencies
    *   **Then** the computation function is called only once (value is cached).
*   **Given** a `rxprop.computed` property whose dependencies have changed
    *   **When** the property is accessed
    *   **Then** the computation function is called again.

#### 2.2.4 Notification on Change
*   **Given** a `rxprop.computed` property and an active watcher on it
    *   **When** a dependency changes, causing the computed property's value to change
    *   **Then** the watcher is notified with the new computed value.
*   **Given** a `rxprop.computed` property and an active watcher on it
    *   **When** a dependency changes, but the computed property's value remains the same (e.g., `computed = dep1 > 0 or dep2 > 0`)
    *   **Then** the watcher is NOT notified (to be confirmed, ideal behavior).

#### 2.2.5 Nested Computed Properties
*   **Given** `computed1` depends on `value1`, and `computed2` depends on `computed1`
    *   **When** `value1` changes
    *   **Then** `computed1` re-evaluates.
    *   **And Then** `computed2` re-evaluates.
    *   **And Then** watchers on `computed2` are notified of its new value.

#### 2.2.6 Attempting to Set a Computed Property
*   **Given** a `rxprop.computed` property (without an explicit setter)
    *   **When** an attempt is made to set its value
    *   **Then** an appropriate error (e.g., `AttributeError` or specific property error indicating it's read-only) is raised.

---

### 2.3 `rxprop.reactive_property`

#### 2.3.1 Custom Getter and Setter
*   **Given** a class with an `rxprop.reactive_property` using a custom getter
    *   **When** the property is accessed
    *   **Then** the custom getter is called and its return value is provided.
*   **Given** a class with an `rxprop.reactive_property` using a custom setter
    *   **When** a value is assigned to the property
    *   **Then** the custom setter is called with the instance and the assigned value.

#### 2.3.2 Notification
*   **Given** an `rxprop.reactive_property` (implicitly, its setter should trigger notification) and an active watcher
    *   **When** the property is set (and its underlying value changes, triggering notification from the setter logic)
    *   **Then** the watcher is notified.

---

### 2.4 `rxprop.watch`

#### 2.4.1 Watching `rxprop.value`
*   **Given** an `rxprop.value` property on an instance
    *   **When** `rxprop.watch` is called on the instance and property
    *   **Then** an async iterator is returned.
*   **Given** an `rxprop.value` property on an instance with an initial value
    *   **When** `rxprop.watch` is called and iteration begins on the returned async iterator
    *   **Then** the async iterator immediately yields the current (initial) value of the property.
*   **Given** an async iterator from `rxprop.watch` on a `value` property
    *   **When** the `value` property is set to a new value
    *   **Then** the async iterator yields the new value.
*   **Given** an async iterator from `rxprop.watch`
    *   **When** the property is set multiple times in quick succession
    *   **Then** the async iterator yields the latest value (or all intermediate if guaranteed, check docs/implementation - stub says "NOT guaranteed to yield intermediate values").

#### 2.4.2 Watching `rxprop.computed`
*   **Given** an `rxprop.computed` property on an instance
    *   **When** `rxprop.watch` is called on the instance and property
    *   **Then** an async iterator is returned.
*   **Given** an `rxprop.computed` property on an instance
    *   **When** `rxprop.watch` is called and iteration begins on the returned async iterator
    *   **Then** the async iterator immediately yields the current computed value of the property.
*   **Given** an async iterator from `rxprop.watch` on a `computed` property
    *   **When** a dependency of the `computed` property changes, causing the computed value to change
    *   **Then** the async iterator yields the new computed value.

#### 2.4.3 Watching by Property Name (String)
*   **Given** an instance with a reactive property named "my_prop"
    *   **When** `rxprop.watch(instance, "my_prop")` is called
    *   **Then** it behaves the same as watching the property object directly.
*   **Given** an instance and a non-existent property name
    *   **When** `rxprop.watch(instance, "non_existent_prop")` is called
    *   **Then** it raises an appropriate error (e.g., `AttributeError`).

#### 2.4.4 Watcher Lifecycle
*   **Given** an async iterator from `rxprop.watch`
    *   **When** the iterator is exhausted or closed (e.g., `async for` loop finishes or `break`)
    *   **Then** the underlying watcher/handler is removed and no longer receives notifications.

---

### 2.5 `rxprop.notifier.Notifier`

#### 2.5.1 Handler Management
*   **Given** a `Notifier` instance
    *   **When** `add_handler` is called with a callable
    *   **Then** the handler is registered.
*   **Given** a `Notifier` instance with a registered handler
    *   **When** `remove_handler` is called with that same handler
    *   **Then** the handler is deregistered.
*   **Given** a `Notifier` instance
    *   **When** `remove_handler` is called with a handler that was not added
    *   **Then** it does not raise an error (graceful failure).

#### 2.5.2 Event Firing
*   **Given** a `Notifier` instance with one or more registered handlers
    *   **When** `fire()` is called
    *   **Then** all registered handlers are executed.
*   **Given** a `Notifier` instance with no registered handlers
    *   **When** `fire()` is called
    *   **Then** no error occurs.

#### 2.5.3 `handler_context`
*   **Given** a `Notifier` and a handler function
    *   **When** `handler_context` is used with the handler
    *   **Then** the handler is active within the context and removed upon exiting.
    *   **And When** `fire()` is called within the context
    *   **Then** the handler is called.
    *   **And When** `fire()` is called after exiting the context
    *   **Then** the handler is NOT called.

#### 2.5.4 `event_context`
*   **Given** a `Notifier`
    *   **When** `event_context` is used
    *   **Then** it provides an `asyncio.Event`.
*   **Given** an `asyncio.Event` from `event_context`
    *   **When** the `Notifier`'s `fire()` method is called
    *   **Then** the `asyncio.Event` is set.
*   **Given** an `asyncio.Event` from `event_context` that has been set
    *   **When** it's awaited
    *   **Then** the await completes.
    *   **And Then** the event should be clear for the next fire (confirm behavior).

---

### 2.6 Dependency Tracking (`listen_for_dependencies`)

*   **Given** a set for storing notifiers and a reactive property
    *   **When** the property is accessed within a `listen_for_dependencies` context manager using that set
    *   **Then** the property's notifier is added to the set.
*   **Given** a set for storing notifiers and multiple reactive properties
    *   **When** these properties are accessed within a `listen_for_dependencies` context
    *   **Then** all their notifiers are added to the set.
*   **Given** a `listen_for_dependencies` context
    *   **When** a non-reactive attribute is accessed within the context
    *   **Then** no error occurs and nothing is added to the dependency set for that access.
*   **Given** existing listeners on a property
    *   **When** `listen_for_dependencies` context is active for that property
    *   **Then** existing listeners are temporarily suppressed.
    *   **And When** the context exits
    *   **Then** existing listeners are restored.

---

### 2.7 `TypedProperty` and Mixins

#### 2.7.1 Basic `TypedProperty` Descriptors
*   **Given** a class with a `TypedProperty` attribute
    *   **When** the attribute is accessed on an instance
    *   **Then** `TypedProperty.__get__` is called, and it should handle its internal logic (likely returning the stored value or calling a getter).
*   **Given** a class with a `TypedProperty` attribute
    *   **When** a value is assigned to the attribute on an instance
    *   **Then** `TypedProperty.__set__` is called.
*   **Given** a class with a `TypedProperty` attribute
    *   **When** `del` is used on the attribute on an instance
    *   **Then** `TypedProperty.__delete__` is called.
*   **Given** a class definition with a `TypedProperty`
    *   **When** the class is being defined
    *   **Then** `TypedProperty.__set_name__` is called with the owner class and property name.

#### 2.7.2 `GetterMixin`
*   **Given** a `TypedProperty` subclassed from/mixed with `GetterMixin` and a custom getter function provided via `fget` or `.getter()`
    *   **When** the property is accessed
    *   **Then** the custom getter function is executed.

#### 2.7.3 `SetterMixin`
*   **Given** a `TypedProperty` subclassed from/mixed with `SetterMixin` and a custom setter function provided via `fset` or `.setter()`
    *   **When** a value is assigned to the property
    *   **Then** the custom setter function is executed.

#### 2.7.4 `DeleterMixin`
*   **Given** a `TypedProperty` subclassed from/mixed with `DeleterMixin` and a custom deleter function provided via `fdel` or `.deleter()`
    *   **When** `del` is used on the property
    *   **Then** the custom deleter function is executed.

#### 2.7.5 `DefaultMixin`
*   **Given** a `TypedProperty` subclassed from/mixed with `DefaultMixin` and a default factory provided
    *   **When** the property is accessed for the first time and no value has been set
    *   **Then** the default factory is called to provide the value.
    *   **And When** the property is accessed again without being set
    *   **Then** the default factory is NOT called again (value is stored).

---

## 3. Prioritization (High-Level)

1.  **P0: Core Functionality**
    *   `rxprop.value`: Basic storage, default value, notification.
    *   `rxprop.computed`: Basic computation, dependency tracking, re-computation, caching, notification.
    *   `rxprop.watch`: Watching `value` and `computed` properties.
    *   `Notifier`: Basic `add_handler`, `remove_handler`, `fire`.
2.  **P1: Advanced/Mixin Functionality**
    *   `rxprop.reactive_property`: Custom getters/setters.
    *   `listen_for_dependencies`: Correct context management.
    *   `Notifier`: `handler_context`, `event_context`.
    *   `TypedProperty` and its mixins: Ensuring descriptor protocol and mixin behaviors are correct.
    *   Edge cases for all P0 items (e.g., setting to same value, multiple quick updates for watchers).
3.  **P2: Less Critical/Error Handling**
    *   Watching non-existent properties by name.
    *   Interactions between deeply nested computed properties.

## 4. Test Structure

*   Tests will be located in `Tests/rxprop/`.
*   File naming: `test_<feature>_<behaviour>.py` (e.g., `test_value_property_basics.py`, `test_computed_property_dependencies.py`).
*   Test function naming: `test_<action>_when_<condition>_then_<expected>()`.
*   A `test_typing.py` will be created to ensure static type checking passes with `pyright`.

## 5. Out of Scope for Initial Plan (Potentially Future)

*   Performance testing under high load / many properties / frequent updates.
*   Complex interactions with external async libraries beyond basic `asyncio.Event`.
*   Thread safety (assuming primarily single-threaded async usage, but to be confirmed if multi-threading is a target).

## 6. Status Key

*   `⚪️ Not Started`
*   `🟡 In Progress`
*   `✅ Done`
*   `⚠️ Needs Discussion`
*   `🚧 Blocked`

(Each scenario will be updated with a status marker as development progresses)

---
**Initial Status for all scenarios: `⚪️ Not Started`** 