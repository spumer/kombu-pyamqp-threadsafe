import kombu.simple


class SimpleBase(kombu.simple.SimpleBase):
    def get(self, block: bool = True, timeout: "float | None" = None):
        try:
            return super().get(block, timeout)
        except self.Empty:
            if self.buffer:
                # it's possible to receive messages in other place
                # re-check we are not missing it
                try:
                    return self.buffer.popleft()
                except IndexError:
                    # so, someone was faster
                    pass
            # nothing in a queue actually
            raise


class SimpleQueue(SimpleBase, kombu.simple.SimpleQueue):
    pass


class SimpleBuffer(SimpleBase, kombu.simple.SimpleBuffer):
    pass
