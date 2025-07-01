class Valuer:
    __slots__ = ['t', 'v']

    def __init__(self, t, v):
        self.t = t
        self.v = v
    #
    # def __repr__(self):
    #     return f"Value(t={self.t.time()}, v={self.v})"