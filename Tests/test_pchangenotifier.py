import rxprop as rx


def test_pchangenotifier():

    class MutableObject(rx.ChangeNotifierBase):
        def __init__(self):
            super().__init__()
            self.value = 0
        
        def set_value(self, value: int):
            self.value = value
            self.on_change.fire(None)

    received_values: list[int] = []
    def handler(_: None):
        received_values.append(obj.value)
    
    obj = MutableObject()
    assert isinstance(obj, rx.PChangeNotifier)
    assert obj.value == 0

    with obj.on_change.bind(handler):
        obj.set_value(1)
        obj.set_value(2)
        obj.set_value(3)
        obj.set_value(3)
    obj.set_value(4)

    assert obj.value == 4
    assert received_values == [1, 2, 3, 3]

