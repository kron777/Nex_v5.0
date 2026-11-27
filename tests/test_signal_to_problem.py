from types import SimpleNamespace

from theory_x.signals import prose_stats, signal_to_problem


class _OneIterationStop:
    def __init__(self):
        self.stopped = False

    def is_set(self):
        return self.stopped

    def wait(self, timeout):
        self.stopped = True
        return True


def test_signal_to_problem_loop_uses_shared_prose_stats_writer(monkeypatch):
    writer = object()
    reader = object()
    state = SimpleNamespace(
        writers={"beliefs": writer},
        readers={"beliefs": reader},
    )
    writer_calls = []
    direct_calls = []

    def build(shared_writer, shared_reader):
        writer_calls.append((shared_writer, shared_reader))
        return 17

    def build_direct(*args, **kwargs):
        direct_calls.append((args, kwargs))
        return 17

    monkeypatch.setattr(prose_stats, "build", build)
    monkeypatch.setattr(prose_stats, "build_direct", build_direct)
    monkeypatch.setattr(
        signal_to_problem,
        "signal_to_problem_tick",
        lambda: {"opened": 0},
    )

    signal_to_problem.signal_to_problem_loop(state, _OneIterationStop())

    assert writer_calls == [(writer, reader)]
    assert direct_calls == []
