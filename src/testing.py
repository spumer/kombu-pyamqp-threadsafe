import threading


class PropagatingThread(threading.Thread):
    """Thread that propagates exceptions to the joining thread."""

    def run(self):
        self.exc = None
        self.ret = None
        try:
            if self._target:
                self.ret = self._target(*self._args, **self._kwargs)
        except BaseException as e:
            self.exc = e
        finally:
            # Avoid a refcycle if the thread is running a function with
            # an argument that has a member that points to the thread.
            del self._target, self._args, self._kwargs

    def join(self, *args, **kw):
        super().join(*args, **kw)
        if self.exc:
            raise self.exc  # possible refcycle, see .run() to details
        return self.ret
