
class A():
    def __init__(self):
        pass

    def setConfig(self, config):
        self.config = D()
        self.config.a = config.a
        self.config.b = config.b
        self.config.c = C()
        self.config.d = config.d
        self.config.c.d = config.c.d
        self.config.c.e = config.c.e
        self.config.c.f = config.c.f

class B():
    def __init__(self):
        self.a = None
        self.b = None
        self.c = None

class C():
    pass

class D():
    pass

def test():
    b = B()
    b.a = "a"
    b.b = "b"
    c = C()
    c.d = "c.d"
    c.e = "c.e"
    b.c = c

    a = A()
    a.setConfig(b)
    print a.a
    print a.b
    print a.c.d
    print a.c.e
    print a.c.f

if __name__=='__main__':
    test()

