import gc, weakref

import rxprop as rx


def test_notify():
    # Given a handler bound to a notifier,
    # when the notifier is fired,
    # then the handler should be called.
    # when the handler is unbound,
    # then the handler should not be called.
    received_values: list[int] = []
    def handler(value: int):
        received_values.append(value)
    notifier = rx.Notifier[int]()

    with notifier.bind(handler):
        notifier.fire(1)
        notifier.fire(2)
        notifier.fire(3)
    notifier.fire(4)

    assert received_values == [1, 2, 3]


def test_handler_keepalive():
    # Given a handler bound to a notifier,
    # when the handler goes out of scope,
    # then the handler is not GC'd,
    #   and should be called when the notifier is fired.
    received_values: list[int] = []
    def handler(value: int):
        received_values.append(value)
    notifier = rx.Notifier[int]()

    with notifier.bind(handler):
        handler = lambda value: None
        gc.collect()
        notifier.fire(1)
    assert received_values == [1]


def test_notifier_no_keepalive():
    # Given a handler bound to a notifier,
    # when the notifier goes out of scope,
    # then the notifier is GC'd,
    #   because it is not kept alive by the binding.
    received_values: list[int] = []
    def handler(value: int):
        received_values.append(value)
    notifier = rx.Notifier[int]()
    weak_notifier = weakref.ref(notifier)

    with notifier.bind(handler):
        notifier.fire(1)
        notifier = None
        gc.collect()
        assert weak_notifier() is None
